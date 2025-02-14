# tests/conftest.py
import pytest
from unittest.mock import Mock, patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config.ConfigLoader import (
    AppConfig, 
    ModelConfig, 
    DirectoryConfig, 
    PathConfig, 
    FlaskConfig, 
    ReferenceAudioConfig, 
    CleanupConfig
)
from src.core.tts_manager import TTSManager
import numpy as np
from flask import Flask

@pytest.fixture
def test_config():
    """Create actual config instances with test values"""
    models = ModelConfig(
        xtts_base_model="tts_models/multilingual/multi-dataset/xtts_v2",
        xtts_vietnamese="capleaf/viXTTS",
        indic_model="ai4bharat/indic-parler-tts-pretrained"
    )
    
    directories = DirectoryConfig(
        audio_output_dir="audio",
        vietnamese_model_dir="vn_model"
    )
    
    paths = PathConfig(
        key_path=r"C:/Users/Cihan/Desktop/NeviTechTTS/src/certificates/_.klassifier.com.key",
        cert_path=r"C:/Users/Cihan/Desktop/NeviTechTTS/src/certificates/combined_certificate.crt",
        google_credentials=r"C:/Users/Cihan/Desktop/NeviTechTTS/src/certificates/klassifier-translation-322b40f8ffce.json"
    )
    
    flask = FlaskConfig(
        port=5000,
        host="0.0.0.0"
    )
    
    reference_audio_paths = ReferenceAudioConfig(
        male=r"C:/Users/Cihan/Desktop/NeviTechTTS/src/references/man.wav",
        female=r"C:/Users/Cihan/Desktop/NeviTechTTS/src/references/woman.wav"
    )
    
    cleanup = CleanupConfig(
        max_age_hours=24,
        min_free_space_mb=1000,
        cleanup_interval_minutes=30
    )
    
    return AppConfig(
        models=models,
        directories=directories,
        paths=paths,
        flask=flask,
        reference_audio_paths=reference_audio_paths,
        cleanup=cleanup,
        kokoro_speed=1.0
    )

@pytest.fixture
def mock_model():
    model = Mock()
    model.get_conditioning_latents.return_value = (Mock(), Mock())
    model.inference.return_value = {"wav": np.zeros(1000)}
    model.config.text_encoder._name_or_path = "test_encoder_path"
    model.config.sampling_rate = 24000
    return model

@pytest.fixture
def mock_tokenizer():
    tokenizer = Mock()
    tokenizer.return_value.to.return_value = Mock(
        input_ids=Mock(),
        attention_mask=Mock()
    )
    return tokenizer

@pytest.fixture
def mock_pipeline():
    from core.constants import KOKORO_VOICE_CHOICES
    pipeline = Mock()
    pipeline.voices = {code: Mock() for _, code, _ in KOKORO_VOICE_CHOICES}
    pipeline.__call__.return_value = [("test", "test", np.zeros(1000))]
    return pipeline

@pytest.fixture
def mock_polly_client():
    with patch('boto3.client') as mock_client:
        client = mock_client.return_value
        client.describe_voices.return_value = {
            'Voices': [
                {
                    'Id': 'Joanna',
                    'Name': 'Joanna',
                    'LanguageCode': 'en-US',
                    'LanguageName': 'English (US)',
                    'Gender': 'Female',
                    'SupportedEngines': ['neural']
                }
            ]
        }
        yield client

# TTS Manager and App fixtures
@pytest.fixture
def tts_manager(test_config):
    with patch('core.tts_manager.PollyService'), \
         patch('core.tts_manager.XttsService'), \
         patch('core.tts_manager.ViXttsService'), \
         patch('core.tts_manager.IndicService'), \
         patch('core.tts_manager.KokoroService'), \
         patch('core.tts_manager.AudioFileCleanup'):
        manager = TTSManager(test_config)
        return manager

@pytest.fixture
def app():
    """Create Flask application for testing"""
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app, test_config):
    """Create test client with TTS manager"""
    with patch('core.tts_manager.PollyService'), \
         patch('core.tts_manager.XttsService'), \
         patch('core.tts_manager.ViXttsService'), \
         patch('core.tts_manager.IndicService'), \
         patch('core.tts_manager.KokoroService'), \
         patch('core.tts_manager.AudioFileCleanup'):
        
        app.tts_manager = TTSManager(test_config)
        return app.test_client()

@pytest.fixture
def tmp_audio_dir(tmp_path):
    """Create a temporary audio directory for testing"""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return audio_dir