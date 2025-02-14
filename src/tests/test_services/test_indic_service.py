# tests/test_services/test_indic_service.py
import pytest
from unittest.mock import Mock, patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.IndicService import IndicService
from core.error_handlers import IndicParlerError
from core.constants import INDIC_VOICES, INDIC_LANG_CODES
from config.ConfigLoader import AppConfig
import torch
import numpy as np

@pytest.fixture
def indic_service(test_config, mock_model, mock_tokenizer):
    with patch('services.IndicService.ParlerTTSForConditionalGeneration.from_pretrained', 
              return_value=mock_model), \
         patch('services.IndicService.AutoTokenizer.from_pretrained', 
              return_value=mock_tokenizer):
        service = IndicService(test_config)
        service.model = mock_model
        service.tokenizer = mock_tokenizer
        service.description_tokenizer = mock_tokenizer
        return service