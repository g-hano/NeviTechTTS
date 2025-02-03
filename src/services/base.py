import torch

class BaseService:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.languages = []
    
    def get_supported_languages(self):
        return self.languages
    
    def get_voices(self):
        raise NotImplementedError

    def synthesize(self, text, voice_id, session_id):
        raise NotImplementedError
    