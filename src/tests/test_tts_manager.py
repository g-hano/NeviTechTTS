# tests/test_tts_manager.py
import pytest
from unittest.mock import Mock, patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.tts_manager import TTSManager
from src.core.error_handlers import TTSBaseError
from flask import Flask

# Flask app fixture specific to TTS Manager tests
@pytest.fixture
def app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app, test_config):
    # Create a TTS manager with mocked services
    with patch('core.tts_manager.PollyService'), \
         patch('core.tts_manager.XttsService'), \
         patch('core.tts_manager.ViXttsService'), \
         patch('core.tts_manager.IndicService'), \
         patch('core.tts_manager.KokoroService'), \
         patch('core.tts_manager.AudioFileCleanup'):
        
        app.tts_manager = TTSManager(test_config)
        return app.test_client()

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'healthy'}

def test_get_voices(client):
    response = client.get('/voices')
    assert response.status_code == 200
    data = response.json
    assert 'voices' in data
    assert isinstance(data['voices'], dict)

def test_clear_session(client):
    session_id = "test_session"
    response = client.post(f'/clear/{session_id}')
    assert response.status_code == 200
    assert response.json == {'success': True}

def test_generate_realtime_missing_params(client):
    response = client.post('/generate/realtime')
    assert response.status_code == 400
    assert 'error' in response.json

def test_generate_realtime_success(client, tmp_audio_dir):
    data = {
        'text': 'Hello world',
        'voice_id': 'test_voice',
        'session_id': 'test_session'
    }
    
    # Mock the synthesize_speech method
    def mock_synthesize(text, voice_id, session_id):
        return "test_output.wav"
    
    with patch.object(client.application.tts_manager, 'synthesize_speech', 
                     side_effect=mock_synthesize):
        response = client.post('/generate/realtime', json=data)
        assert response.status_code == 200
        assert 'audio_file' in response.json

def test_generate_realtime_error(client):
    data = {
        'text': 'Hello world',
        'voice_id': 'test_voice',
        'session_id': 'test_session'
    }
    
    # Mock synthesis failure
    with patch.object(client.application.tts_manager, 'synthesize_speech', 
                     side_effect=TTSBaseError("Test error")):
        response = client.post('/generate/realtime', json=data)
        assert response.status_code == 500
        assert 'error' in response.json

def test_tts_manager_initialization(test_config):
    with patch('core.tts_manager.PollyService'), \
         patch('core.tts_manager.XttsService'), \
         patch('core.tts_manager.ViXttsService'), \
         patch('core.tts_manager.IndicService'), \
         patch('core.tts_manager.KokoroService'), \
         patch('core.tts_manager.AudioFileCleanup'):
        
        manager = TTSManager(test_config)
        assert manager is not None
        assert hasattr(manager, '_voices')