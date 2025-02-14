from typing import Dict

class TranslationError(Exception):
    """Custom exception for translation errors"""
    def __init__(self, message: str, details: Dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class TTSBaseError(Exception):
    """Base class for TTS-related errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class PollyError(TTSBaseError):
    """Errors specific to AWS Polly synthesis"""
    def __init__(self, message: str, aws_error_code: str = None, details: dict = None):
        super().__init__(message, details)
        self.aws_error_code = aws_error_code

class XTTSError(TTSBaseError):
    """Errors specific to XTTS synthesis"""
    def __init__(self, message: str, model_state: str = None, details: dict = None):
        super().__init__(message, details)
        self.model_state = model_state

class KokoroError(TTSBaseError):
    """Errors specific to Kokoro synthesis"""
    def __init__(self, message: str, language_code: str = None, details: dict = None):
        super().__init__(message, details)
        self.language_code = language_code

class VietnameseXTTSError(TTSBaseError):
    """Errors specific to Vietnamese XTTS synthesis"""
    def __init__(self, message: str, model_state: str = None, details: dict = None):
        super().__init__(message, details)
        self.model_state = model_state

class IndicParlerError(TTSBaseError):
    """Errors specific to Indic Parler synthesis"""
    def __init__(self, message: str, language: str = None, details: dict = None):
        super().__init__(message, details)
        self.language = language

class CudaError(TTSBaseError):
    """Specific error class for CUDA-related issues"""
    def __init__(self, message: str, model_name: str = None, details: dict = None):
        super().__init__(message, details)
        self.model_name = model_name
        
    @staticmethod
    def is_cuda_error(error: Exception) -> bool:
        """Check if an error is CUDA-related"""
        error_str = str(error).lower()
        cuda_keywords = [
            'cuda', 'gpu', 'out of memory', 
            'device-side assert', 'cudnn', 'cublas',
            'cuda runtime error', 'cuda error'
        ]
        return any(keyword in error_str for keyword in cuda_keywords)


def handle_tts_error(error: TTSBaseError) -> tuple:
    """
    Handles various TTS errors and returns appropriate response tuple
    Returns: (response_dict, status_code)
    """
    base_response = {
        "success": False,
        "error": str(error.message),
        "details": error.details
    }
    
    if isinstance(error, CudaError):
        base_response.update({
            "error_type": "cuda",
            "model_name": error.model_name,
            "requires_restart": True
        })
        return base_response, 503
    
    if isinstance(error, PollyError):
        base_response.update({
            "error_type": "polly",
            "aws_error_code": error.aws_error_code
        })
        return base_response, 500
        
    elif isinstance(error, XTTSError):
        base_response.update({
            "error_type": "xtts",
            "model_state": error.model_state
        })
        return base_response, 503
        
    elif isinstance(error, KokoroError):
        base_response.update({
            "error_type": "kokoro",
            "language_code": error.language_code
        })
        return base_response, 503
        
    elif isinstance(error, VietnameseXTTSError):
        base_response.update({
            "error_type": "vietnamese_xtts",
            "model_state": error.model_state
        })
        return base_response, 503
        
    elif isinstance(error, IndicParlerError):
        base_response.update({
            "error_type": "indic_parler",
            "language": error.language
        })
        return base_response, 503
        
    else:
        base_response.update({
            "error_type": "unknown"
        })
        return base_response, 500
