from TTS.utils.manage import ModelManager
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir
import numpy as np
from scipy.io.wavfile import write
import time
from pathlib import Path

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.constants import XTTS_LANGUAGE_NAMES, XTTS_SAMPLE_RATE
from core.error_handlers import XTTSError
from .base import BaseService
from voice_info_engine import VoiceInfo

class XttsService(BaseService):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.languages = XTTS_LANGUAGE_NAMES
        model_name = config.models.xtts_base_model
        self.model = self.get_xtts(model_name)
        self.speakers = {
            "male": config.reference_audio_paths.male,
            "female": config.reference_audio_paths.female
        }
            
    def get_xtts(self, xtts_base_model_name):
        """Initialize and return the XTTS model"""
        try:
            ModelManager().download_model(xtts_base_model_name)
            model_path = os.path.join(get_user_data_dir("tts"), xtts_base_model_name.replace("/", "--"))
            config = XttsConfig()
            config.load_json(os.path.join(model_path, "config.json"))
            xtts_base_model = Xtts.init_from_config(config)
            xtts_base_model.load_checkpoint(config, checkpoint_dir=model_path, eval=True)
            return xtts_base_model.to(self.device)
        except Exception as e:
            raise XTTSError(
                message=f"Failed to initialize XTTS model: {str(e)}",
                model_state="initialization_failed"
            )

    def get_voices(self):
        grouped_voices = {}
        for code, name in sorted(XTTS_LANGUAGE_NAMES.items()):
            if name not in grouped_voices:
                grouped_voices[name] = []
            for gender in ['Male', 'Female']:
                voice_info = VoiceInfo(
                    id=f'xtts_{code}_{gender.lower()}',
                    name=f'XTTS {gender} Voice ({name})',
                    description='Local XTTS neural voice',
                    language_name=name,
                    engine='xtts',
                    gender=gender
                )
                grouped_voices[name].append(voice_info)
        return grouped_voices

    def synthesize(self, text: str, voice_id: str, session_id: str) -> str:
        """
        Synthesize speech using XTTS
        Returns: Path to the generated audio file
        """
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_dir = self.base_dir / self.config.directories.audio_output_dir
            output_path = output_dir / output_filename

            _, lang_code, gender = voice_id.split('_')
            reference_audio = self.speakers[gender.lower()]
            
            if not os.path.exists(reference_audio):
                raise XTTSError(
                    message=f"Reference audio file not found: {reference_audio}",
                    model_state="reference_missing"
                )
            
            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=reference_audio,
                gpt_cond_len=30,
                gpt_cond_chunk_len=4,
                max_ref_length=60
            )
            
            out = self.model.inference(
                text,
                lang_code,
                gpt_cond_latent,
                speaker_embedding,
                temperature=0.75,
                repetition_penalty=5.0
            )    

            audio_array = np.array(out["wav"])
            write(output_path, XTTS_SAMPLE_RATE, audio_array)
            
            if os.path.exists(output_path):
                return output_filename
                
            raise XTTSError(
                message="Failed to save audio file",
                model_state="save_failed",
                details={"output_path": output_path}
            )

        except XTTSError:
            raise
        except Exception as e:
            raise XTTSError(
                message=f"XTTS synthesis failed: {str(e)}",
                model_state="inference_failed",
                details={"lang_code": lang_code, "gender": gender}
            )