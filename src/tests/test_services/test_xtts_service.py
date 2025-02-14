# tests/test_services/test_xtts_service.py
import pytest
from unittest.mock import patch

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.XttsService import XttsService

@pytest.fixture
def xtts_service(test_config, mock_model):
    with patch('services.XttsService.Xtts') as mock_xtts, \
         patch('services.XttsService.ModelManager'), \
         patch('services.XttsService.get_user_data_dir', return_value="test_dir"), \
         patch('os.path.exists', return_value=True):
        mock_xtts.init_from_config.return_value = mock_model
        service = XttsService(test_config)
        return service