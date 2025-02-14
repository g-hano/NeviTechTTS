# tests/test_services/test_polly_service.py
import pytest
from unittest.mock import patch
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.PollyService import PollyService
@pytest.fixture
def polly_service(test_config, mock_polly_client):
    with patch('services.PollyService.boto3.client', return_value=mock_polly_client):
        service = PollyService(test_config)
        return service