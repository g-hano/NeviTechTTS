from pathlib import Path
import time
from scipy.io.wavfile import write

from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.constants import INDIC_VOICES, INDIC_LANG_CODES
from core.error_handlers import IndicParlerError
from .base import BaseService
from core.voice_info_engine import VoiceInfo

class IndicService(BaseService):
    def __init__(self, config: AppConfig):
        super().__init__()
        model_name = config.models.indic_model
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config = config
        self.languages = list(INDIC_LANG_CODES.keys())
        self.model = ParlerTTSForConditionalGeneration.from_pretrained(model_name).to(self.device)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.description_tokenizer = AutoTokenizer.from_pretrained(self.model.config.text_encoder._name_or_path)

    def get_voices(self):
        try:
            grouped_voices = {}
            for language, voices in INDIC_VOICES.items():
                grouped_voices[language] = []
                for voice_name, gender in voices:
                    voice_info = VoiceInfo(
                        id=f'indic_{INDIC_LANG_CODES[language]}_{voice_name.lower()}',
                        name=f"{voice_name} ({language})",
                        description=f'Indic Parler TTS neural voice for {language}',
                        language_name=language,
                        engine='indic',
                        gender=gender
                    )
                    grouped_voices[language].append(voice_info)
            return grouped_voices
        except Exception as e:
            IndicParlerError(f"Error getting Indic voices: {e}")
            return {}
        
    def synthesize(self, text, voice_id, session_id):
        lang_code = None
        voice_name = None
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_dir = self.base_dir / self.config.directories.audio_output_dir
            output_path = output_dir / output_filename
            
            _, lang_code, voice_name = voice_id.split('_')
            voice_name = voice_name.capitalize()

            try:
                language = next(lang for lang, code in INDIC_LANG_CODES.items() 
                      if INDIC_LANG_CODES[lang] == lang_code)
            except StopIteration:
                raise IndicParlerError(
                    message=f"Unsupported language code: {lang_code}",
                    language=lang_code,
                    details={"available_codes": list(self.indic_lang_codes.values())}
                )

            # Check if voice exists for the language
            voice_exists = False
            for voice_tuple in INDIC_VOICES.get(language, []):
                if voice_tuple[0].lower() == voice_name.lower():
                    voice_exists = True
                    break

            if not voice_exists:
                raise IndicParlerError(
                    message=f"Voice {voice_name} not found for language {language}",
                    language=language,
                    details={
                        "requested_voice": voice_name,
                        "available_voices": [v[0] for v in INDIC_VOICES.get(language, [])]
                    }
                )

            # Prepare description
            description = f"{voice_name} delivers a slightly expressive and animated speech with a moderate speed and pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up."

            try:
                description_inputs = self.description_tokenizer(
                    description, 
                    return_tensors="pt"
                ).to(self.device)
            except Exception as e:
                raise IndicParlerError(
                    message=f"Description tokenization failed: {str(e)}",
                    language=language,
                    details={"description": description}
                )

            try:
                prompt_inputs = self.tokenizer(
                    text, 
                    return_tensors="pt"
                ).to(self.device)
            except Exception as e:
                raise IndicParlerError(
                    message=f"Text tokenization failed: {str(e)}",
                    language=language,
                    details={"text": text}
                )

            try:
                generation = self.model.generate(
                    input_ids=description_inputs.input_ids,
                    attention_mask=description_inputs.attention_mask,
                    prompt_input_ids=prompt_inputs.input_ids,
                    prompt_attention_mask=prompt_inputs.attention_mask
                )
            except Exception as e:
                raise IndicParlerError(
                    message=f"Audio generation failed: {str(e)}",
                    language=language,
                    details={
                        "text": text,
                        "voice": voice_name,
                        "model_state": "generation_failed"
                    }
                )

            # Convert to numpy and save
            audio_array = generation.cpu().numpy().squeeze()
            sf.write(str(output_path), audio_array, self.model.config.sampling_rate)
            
            if output_path.exists():
                return output_filename
            
            raise IndicParlerError(
                message=f"Audio saving failed: {str(e)}",
                language=language,
                details={
                    "output_path": output_path,
                    "sample_rate": self.model.config.sampling_rate
                }
            )

        except IndicParlerError:
            raise
        except Exception as e:
            raise IndicParlerError(
                message=f"Unexpected error in Indic Parler TTS: {str(e)}",
                language=lang_code,
                details={
                    "voice": voice_name,
                    "text": text
                }
            )
        except Exception as e:
            raise e
