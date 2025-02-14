# tests/test_error_handlers.py
import pytest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.error_handlers import (
    TTSBaseError, PollyError, XTTSError, KokoroError,
    VietnameseXTTSError, IndicParlerError, handle_tts_error
)

def test_tts_base_error():
    error = TTSBaseError("Test error", {"detail": "test"})
    assert error.message == "Test error"
    assert error.details == {"detail": "test"}

def test_polly_error():
    error = PollyError("Polly error", "InvalidSampleRate", {"rate": "16000"})
    assert error.message == "Polly error"
    assert error.aws_error_code == "InvalidSampleRate"
    assert error.details == {"rate": "16000"}

def test_error_handler():
    error = PollyError("Test Polly error", "InvalidInput")
    response, status_code = handle_tts_error(error)
    assert response["success"] is False
    assert response["error_type"] == "polly"
    assert status_code == 500