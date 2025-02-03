import logging
from typing import Dict, Optional

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.ConfigLoader import AppConfig

from core.translator import Translator
from core.file_cleanup import AudioFileCleanup
from core.error_handlers import TTSBaseError
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
        self.polly_service = PollyService(self.config)
        print("Polly is ready!")
        self.xtts = XttsService(self.config)
        print("xtts-v2 is ready!")
        self.vi_xtts = ViXttsService(self.config)
        print("Vietnamese XTTS is ready!")
        self.indic = IndicService(self.config)
        print("Indic Parler TTS is ready!")
        self.kokoro = KokoroService(self.config)
        print("Kokoro pipelines are ready!")

        self.service_map = {
            'xtts_': self.xtts,
            'kokoro_': self.kokoro,
            'vi_xtts': self.vi_xtts,
            'indic_': self.indic
        }

        self.speech_queue = {}
        self.translator = Translator(self.config)

    def _update_voices(self):
        """Update available voices from all services"""
        try:
            grouped_voices = {
                VoiceEngine.POLLY.value: self.polly_service.get_voices(),
                VoiceEngine.XTTS.value: self.xtts.get_voices(),
                VoiceEngine.KOKORO.value: self.kokoro.get_voices(),
                VoiceEngine.VIETNAMESE_XTTS.value: self.vi_xtts.get_voices(),
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
    
    def synthesize_speech(self, text: str, voice_id: str, session_id: str) -> Optional[str]:
        try:
            # Get service based on voice_id prefix
            service = next(
                (service for prefix, service in self.service_map.items() 
                 if voice_id.startswith(prefix)),
                self.polly_service  # Default to Polly if no prefix matches
            )
            
            return service.synthesize(text, voice_id, session_id)

        except TTSBaseError:
            raise
        except Exception as e:
            logging.error(f"Unexpected error in speech synthesis: {e}")
            raise TTSBaseError(f"Unexpected error: {str(e)}")

    def clear_session(self, session_id: str):
        """Clear session data"""
        if session_id in self.speech_queue:
            del self.speech_queue[session_id]

    def reinitialize(self):
        """Reinitialize all services"""
        # Stop cleanup service
        self.cleanup_service.stop()
        
        # Reinitialize other services
        self.init_class()
        self._update_voices()
        
        # Restart cleanup service
        self.cleanup_service.start()

    def __del__(self):
        """Cleanup when the manager is destroyed"""
        if hasattr(self, 'cleanup_service'):
            self.cleanup_service.stop()
