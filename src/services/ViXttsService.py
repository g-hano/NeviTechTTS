from TTS.utils.manage import ModelManager
from TTS.tts.configs.xtts_config import XttsConfig
from TTS.tts.models.xtts import Xtts
from TTS.utils.generic_utils import get_user_data_dir
from pathlib import Path
import time
from scipy.io.wavfile import write
from huggingface_hub import snapshot_download

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.constants import XTTS_SAMPLE_RATE
from core.error_handlers import VietnameseXTTSError
from .base import BaseService
from voice_info_engine import VoiceInfo

class ViXttsService(BaseService):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.languages = ["Vietnamese"]
        self.speakers = {
            "male": config.reference_audio_paths.male,
            "female": config.reference_audio_paths.female
        }
        self.config = config
        # Set up paths
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_dir = self.base_dir / config.directories.vietnamese_model_dir
        
        # Download model if not exists
        if not self.model_dir.exists():
            print("Downloading Vietnamese model from Hugging Face...")
            snapshot_download(
                repo_id=config.models.xtts_vietnamese,
                repo_type="model",
                local_dir=str(self.model_dir)
            )
            print("Vietnamese model downloaded successfully!")
            
        # Initialize model
        self.model = self.get_vietnamese_xtts(self.model_dir)

    def get_vietnamese_xtts(self, model_path):
        try:
            if not model_path.exists():
                raise VietnameseXTTSError(
                    message=f"Model directory not found: {model_path}",
                    model_state="not_found"
                )

            vn_config = XttsConfig()
            config_path = model_path / "config.json"
            vn_config.load_json(str(config_path))
            
            xtts_vietnamese_model = Xtts.init_from_config(vn_config)
            xtts_vietnamese_model.load_checkpoint(vn_config, checkpoint_dir=str(model_path))
            xtts_vietnamese_model.eval()
            return xtts_vietnamese_model.to(self.device)
        except Exception as e:
            raise VietnameseXTTSError(
                message=f"Failed to initialize Vietnamese XTTS model: {str(e)}",
                model_state="initialization_failed"
            )

    def get_voices(self):
        return {
            "Vietnamese": [
                VoiceInfo(
                    id='vi_xtts_female',
                    name='Vietnamese XTTS Female',
                    description='Vietnamese XTTS neural voice',
                    language_name='Vietnamese',
                    engine='vi_xtts',
                    gender='Female'
                ),
                VoiceInfo(
                    id='vi_xtts_male',
                    name='Vietnamese XTTS Male',
                    description='Vietnamese XTTS neural voice',
                    language_name='Vietnamese',
                    engine='vi_xtts',
                    gender='Male'
                )
            ]
        }

    def synthesize(self, text: str, voice_id: str, session_id: str) -> str:
        gender = None
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_dir = self.base_dir / self.config.directories.audio_output_dir
            output_path = output_dir / output_filename

            if not output_dir.exists():
                output_dir.mkdir(parents=True, exist_ok=True)

            # Get gender from voice_id
            gender = voice_id.split('_')[-1]
            reference_audio = self.speakers[gender.lower()]

            if not os.path.exists(reference_audio):
                raise VietnameseXTTSError(
                    message=f"Reference audio file not found: {reference_audio}",
                    model_state="reference_missing"
                )

            gpt_cond_latent, speaker_embedding = self.model.get_conditioning_latents(
                audio_path=reference_audio,
                gpt_cond_len=self.model.config.gpt_cond_len,
                max_ref_length=self.model.config.max_ref_len,
                sound_norm_refs=self.model.config.sound_norm_refs
            )
            
            out = self.model.inference(
                text=text,
                language="vi",
                gpt_cond_latent=gpt_cond_latent,
                speaker_embedding=speaker_embedding,
                temperature=0.3,
                length_penalty=1.0,
                repetition_penalty=10.0,
                top_k=30,
                top_p=0.85
            )
            
            write(str(output_path), XTTS_SAMPLE_RATE, out["wav"])

            if output_path.exists():
                return output_filename

            raise VietnameseXTTSError(
                message="Failed to save audio file",
                model_state="save_failed",
                details={"output_path": str(output_path)}
            )

        except VietnameseXTTSError:
            raise
        except Exception as e:
            raise VietnameseXTTSError(
                message=f"Vietnamese XTTS synthesis failed: {str(e)}",
                model_state="inference_failed",
                details={"gender": gender}
            )