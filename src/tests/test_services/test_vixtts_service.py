# tests/test_services/test_vietnamese_xtts_service.py
import pytest
from unittest.mock import patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ViXttsService import ViXttsService
@pytest.fixture
def vi_xtts_service(test_config, mock_model):
    with patch('services.ViXttsService.Xtts') as mock_xtts, \
         patch('services.ViXttsService.snapshot_download'), \
         patch('pathlib.Path.exists', return_value=True):
        mock_xtts.init_from_config.return_value = mock_model
        service = ViXttsService(test_config)
        return service