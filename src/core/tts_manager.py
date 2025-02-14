import logging
from typing import Optional
import threading
import time
import torch

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.ConfigLoader import AppConfig

from core.translator import Translator
from core.file_cleanup import AudioFileCleanup
from core.error_handlers import CudaError
from core.cuda_monitor import CudaMonitor
from core.voice_info_engine import VoiceEngine

from services.IndicService import IndicService
from services.KokoroService import KokoroService
from services.PollyService import PollyService
from services.ViXttsService import ViXttsService
from services.XttsService import XttsService


class TTSManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self._voices = {}
        self._lock = threading.Lock()
        self.cuda_monitor = CudaMonitor()

        if not self.cuda_monitor.check_cuda():
            logging.error("CUDA initialization failed during TTSManager startup")
            self.cuda_monitor.handle_cuda_error()

        # Initialize recovery tracking dictionaries
        self._recovery_in_progress = {
            'xtts_': False,
            'kokoro_': False,
            'vixtts': False,
            'indic_': False
        }
        self._last_recovery_time = {
            'xtts_': 0,
            'kokoro_': 0,
            'vixtts': 0,
            'indic_': 0
        }
        self._recovery_cooldown = 60  # Minimum seconds between recovery attempts
        
        self.init_class()
        self._update_voices()
        
        # Initialize cleanup service
        self.cleanup_service = AudioFileCleanup(
            directory=self.config.directories.audio_output_dir,
            max_age_hours=config.cleanup.max_age_hours,
            min_free_space_mb=config.cleanup.min_free_space_mb,
            cleanup_interval_minutes=config.cleanup.cleanup_interval_minutes
        )
        self.cleanup_service.start()

    def init_class(self):
        """Initialize all services"""
        try:
            self.polly = PollyService(self.config)
            print("Polly is ready!")
        except Exception as e:
            logging.error(f"Failed to initialize Polly: {e}")
            
        try:
            self.xtts = XttsService(self.config)
            print("xtts-v2 is ready!")
        except Exception as e:
            if "CUDA" in str(e):
                self.cuda_monitor.handle_cuda_error()
            raise

        try:
            self.vixtts = ViXttsService(self.config)
            print("Vietnamese XTTS is ready!")
        except Exception as e:
            if "CUDA" in str(e):
                self.cuda_monitor.handle_cuda_error()
            raise

        try:
            self.indic = IndicService(self.config)
            print("Indic Parler TTS is ready!")
        except Exception as e:
            if "CUDA" in str(e):
                self.cuda_monitor.handle_cuda_error()
            raise

        try:
            self.kokoro = KokoroService(self.config)
            print("Kokoro pipelines are ready!")
        except Exception as e:
            if "CUDA" in str(e):
                self.cuda_monitor.handle_cuda_error()
            raise

        self.service_map = {
            'xtts_': self.xtts,
            'kokoro_': self.kokoro,
            'vixtts': self.vixtts,
            'indic_': self.indic
        }

        self.speech_queue = {}
        self.translator = Translator(self.config)

    def _update_voices(self):
        """Update available voices from all services"""
        try:
            grouped_voices = {
                VoiceEngine.POLLY.value: self.polly.get_voices(),
                VoiceEngine.XTTS.value: self.xtts.get_voices(),
                VoiceEngine.KOKORO.value: self.kokoro.get_voices(),
                VoiceEngine.VIETNAMESE_XTTS.value: self.vixtts.get_voices(),
                VoiceEngine.INDIC_PARLER.value: self.indic.get_voices()
            }
            
            self._voices = {
                engine: {
                    lang: sorted(voices, key=lambda x: x.name)
                    for lang, voices in lang_voices.items()
                    if voices
                }
                for engine, lang_voices in grouped_voices.items()
                if lang_voices
            }
            
        except Exception as e:
            logging.error(f"Error updating voices: {e}")
            self._voices = {}
    
    def get_voices(self):
        """Get all available voices"""
        return self._voices

    def _get_service_for_voice(self, voice_id: str):
        """Get the appropriate service and prefix for a voice ID"""
        for prefix, service in self.service_map.items():
            if voice_id.startswith(prefix):
                return prefix, service
        return None, self.xtts  # Default to Polly

    def synthesize_speech(self, text: str, voice_id: str, session_id: str) -> Optional[str]:
        try:
            # Get service and prefix based on voice_id
            service_prefix, service = self._get_service_for_voice(voice_id)
            
            return service.synthesize(text, voice_id, session_id)

        except Exception as e:
            if "CUDA" in str(e):
                self.cuda_monitor.handle_cuda_error()
            raise

    def _try_recovery(self, service_prefix: str):
        """Attempt recovery for a specific service with cooldown and lock protection"""
        current_time = time.time()
        
        with self._lock:
            if self._recovery_in_progress[service_prefix]:
                return False
                
            if current_time - self._last_recovery_time.get(service_prefix, 0) < self._recovery_cooldown:
                return False
                
            self._recovery_in_progress[service_prefix] = True
        
        try:
            logging.info(f"Starting recovery for service: {service_prefix}")
            self._reinitialize_service(service_prefix)
            self._last_recovery_time[service_prefix] = current_time
            logging.info(f"Service recovery completed successfully for {service_prefix}")
            return True
        except Exception as e:
            logging.error(f"Recovery failed for {service_prefix}: {e}")
            return False
        finally:
            self._recovery_in_progress[service_prefix] = False

    def clear_session(self, session_id: str):
        """Clear session data"""
        if session_id in self.speech_queue:
            del self.speech_queue[session_id]

    def _reinitialize_service(self, service_prefix: str):
        """Reinitialize a specific service"""
        logging.info(f"Reinitializing service: {service_prefix}")
        
        # Clear CUDA cache for GPU services
        if service_prefix in ['xtts_', 'vixtts', 'indic_', 'kokoro_']:
            try:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logging.info(f"CUDA cache cleared for {service_prefix}")
            except Exception as e:
                logging.warning(f"Failed to clear CUDA cache for {service_prefix}: {e}")

        # Reinitialize specific service
        try:
            if service_prefix == 'xtts_':
                self.xtts = XttsService(self.config)
                self.service_map['xtts_'] = self.xtts
            elif service_prefix == 'kokoro_':
                self.kokoro = KokoroService(self.config)
                self.service_map['kokoro_'] = self.kokoro
            elif service_prefix == 'vixtts':
                self.vixtts = ViXttsService(self.config)
                self.service_map['vixtts'] = self.vixtts
            elif service_prefix == 'indic_':
                self.indic = IndicService(self.config)
                self.service_map['indic_'] = self.indic
                
            self._update_voices()  # Update voice list after reinitialization
            logging.info(f"Successfully reinitialized {service_prefix}")
            
        except Exception as e:
            logging.error(f"Failed to reinitialize {service_prefix}: {e}")
            raise

    def reinitialize(self):
        """Full reinitialization of all services - use sparingly"""
        logging.info("Starting full service reinitialization...")
        
        # Stop cleanup service
        self.cleanup_service.stop()
        
        # Clear any existing GPU memory
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logging.info("CUDA cache cleared")
        except Exception as e:
            logging.warning(f"Failed to clear CUDA cache: {e}")
        
        # Reinitialize all services
        self.init_class()
        self._update_voices()
        
        # Restart cleanup service
        self.cleanup_service.start()
        logging.info("Full service reinitialization completed")

    def __del__(self):
        """Cleanup when the manager is destroyed"""
        if hasattr(self, 'cleanup_service'):
            self.cleanup_service.stop()
