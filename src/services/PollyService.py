import boto3
from dotenv import load_dotenv
import time
import numpy as np
from scipy.io.wavfile import write
load_dotenv()
from pathlib import Path
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import AppConfig
from core.constants import POLLY_SAMPLE_RATE, POLLY_LANGUAGE_NAMES
from core.error_handlers import PollyError
from .base import BaseService
from core.voice_info_engine import VoiceInfo

class PollyService(BaseService):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.languages = POLLY_LANGUAGE_NAMES
        self.polly_client = boto3.client(
            'polly',
            region_name=os.getenv("AWS_REGION_NAME"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def get_voices(self):
        try:
            response = self.polly_client.describe_voices()
            voices = sorted(response['Voices'], key=lambda x: (x['LanguageCode'], x['Name']))
            grouped_voices = {}
            
            for voice in voices:
                if 'SupportedEngines' not in voice or 'neural' not in voice['SupportedEngines']:
                    continue
                    
                lang = voice['LanguageCode']
                lang_name = POLLY_LANGUAGE_NAMES.get(lang, lang)
                
                if lang_name not in grouped_voices:
                    grouped_voices[lang_name] = []
                    
                voice_info = VoiceInfo(
                    id=voice['Id'],
                    name=f"{voice['Name']} ({voice['Gender']} - Neural)",
                    description=voice.get('Description', ''),
                    language_name=voice.get('LanguageName', ''),
                    engine="polly",
                    gender=voice['Gender']
                )
                grouped_voices[lang_name].append(voice_info)
                
            return grouped_voices
        except Exception as e:
            PollyError(f"Error fetching Polly voices: {e}")
            return {}

    def synthesize(self, text, voice_id, session_id):
        """
        Synthesize speech using AWS Polly
        Returns: Path to the generated audio file
        """
        try:
            timestamp = int(time.time() * 10000000)
            output_filename = f"realtime_{session_id}_{timestamp}.wav"
            output_dir = self.base_dir / self.config.directories.audio_output_dir
            output_path = output_dir / output_filename
            
            response = self.polly_client.synthesize_speech(
                Engine="neural",
                OutputFormat="pcm",
                Text=text,
                VoiceId=voice_id,
                SampleRate=str(POLLY_SAMPLE_RATE)
            )
            audio_data = response['AudioStream'].read()
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            write(str(output_path), POLLY_SAMPLE_RATE, audio_array)
        
            if output_path.exists():
                return output_filename
                
            raise PollyError(
                message="Failed to save audio file",
                aws_error_code="SAVE_FAILED",
                details={"output_path": output_path}
            )
        
        except Exception as e:
            raise PollyError(
                message=f"Polly synthesis failed: {str(e)}",
                aws_error_code=getattr(e, 'response', {}).get('Error', {}).get('Code'),
                details={"voice_id": voice_id}
            )
