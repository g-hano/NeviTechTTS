# tests/test_services/test_kokoro_service.py
import pytest
from unittest.mock import patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.KokoroService import KokoroService
from core.constants import KOKORO_LANGUAGE_CODES

@pytest.fixture
def kokoro_service(test_config, mock_pipeline):
    with patch('services.KokoroService.KPipeline', return_value=mock_pipeline):
        service = KokoroService(test_config)
        service.pipelines = {code: mock_pipeline for code in KOKORO_LANGUAGE_CODES.values()}
        return service