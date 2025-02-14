from kokoro import KPipeline
from huggingface_hub import hf_hub_download
import logging

import numpy as np
import soundfile as sf
import time
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.constants import KOKORO_LANGUAGE_CODES, KOKORO_VOICE_CHOICES, XTTS_SAMPLE_RATE
from core.error_handlers import KokoroError
from .base import BaseService
from src.core.voice_info_engine import VoiceInfo

class KokoroService(BaseService):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        self.pipelines = self.get_kokoro()
        self.languages = list(KOKORO_LANGUAGE_CODES.keys())
        self._initialize_kokoro_voices()

    def _initialize_kokoro_voices(self):
        """Initialize Kokoro pipelines and load voices"""
        for lang_code in KOKORO_LANGUAGE_CODES.values():
            try:
                pipeline = KPipeline(lang_code=lang_code)
                
                # Get all voices for this language code
                voices_for_lang = [code for _, code, _ in KOKORO_VOICE_CHOICES 
                                 if code.startswith(lang_code)]
                
                # Load each voice
                for voice_code in voices_for_lang:
                    try:
                        pipeline.load_single_voice(voice_code)
                        logging.info(f"Successfully loaded voice: {voice_code}")
                    except Exception as e:
                        logging.error(f"Failed to load voice {voice_code}: {e}")
                
                self.pipelines[lang_code] = pipeline
                logging.info(f"Successfully initialized Kokoro pipeline for {lang_code}")
                
            except Exception as e:
                logging.error(f"Failed to initialize Kokoro pipeline for language {lang_code}: {e}")
                raise KokoroError(
                    message=f"Failed to initialize Kokoro pipeline for language {lang_code}: {e}",
                    language_code=lang_code
                )

    def get_kokoro(self):
        pipelines = {}
        for lang_code in KOKORO_LANGUAGE_CODES.values():
            try:
                pipelines[lang_code] = KPipeline(lang_code=lang_code)
            except Exception as e:
                KokoroError(
                    f"Failed to initialize Kokoro pipeline for language {lang_code}: {e}",
                    lang_code
                )
        return pipelines
    
    def get_voices(self):
        grouped_voices = {"US English": [], "GB English": []}
        for name, code, gender in KOKORO_VOICE_CHOICES:
            # Only add voice if it's been successfully loaded
            lang_code = code[0]
            if lang_code in self.pipelines and code in self.pipelines[lang_code].voices:
                language = "US English" if code.startswith('a') else "GB English"
                voice_info = VoiceInfo(
                    id=f'kokoro_{code}',
                    name=name,
                    description='Local KOKORO neural voice',
                    language_name=language,
                    engine='kokoro',
                    gender='Male' if gender == 'm' else 'Female'
                )
                grouped_voices[language].append(voice_info)
        return grouped_voices

    def synthesize(self, text, voice_id, session_id):
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_dir = self.base_dir / self.config.directories.audio_output_dir
            output_path = output_dir / output_filename

            _, full_voice_name = voice_id.split("kokoro_")
            
            # Get the appropriate pipeline
            lang_code = full_voice_name[0]
            if lang_code not in self.pipelines:
                raise KokoroError(
                    message=f"Kokoro pipeline not initialized for language: {lang_code}",
                    language_code=lang_code
                )
            
            pipeline = self.pipelines[lang_code]
            all_audio = []

            for graphemes, phonemes, audio in pipeline(
                text,
                voice=full_voice_name,
                speed=self.config.kokoro_speed,  # You might want to make this configurable
                split_pattern=r'\n+'
            ):
                all_audio.append(audio)
            
            if not all_audio:
                raise KokoroError(
                    message="No audio generated",
                    language_code=lang_code,
                    details={"voice": full_voice_name}
                )
            
            final_audio = np.concatenate(all_audio)
            sf.write(str(output_path), final_audio, XTTS_SAMPLE_RATE)
            
            if output_path.exists():
                return output_filename
            
            raise KokoroError(
                message="Failed to save audio file",
                model_state="save_failed",
                details={"output_path": str(output_path)}
            )
        
        except Exception as e:
            raise KokoroError(
                message=f"Kokoro synthesis failed: {str(e)}",
                language_code=lang_code,
                details={"voice": full_voice_name}
            )
        
