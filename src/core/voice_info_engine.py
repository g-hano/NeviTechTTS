from dataclasses import dataclass
from enum import Enum

@dataclass
class VoiceInfo:
    id: str
    name: str
    description: str
    language_name: str
    engine: str
    gender: str

class VoiceEngine(Enum):
    POLLY = "Polly"
    XTTS = "XTTS"
    KOKORO = "Kokoro"
    VIETNAMESE_XTTS = "Vietnamese XTTS"
    INDIC_PARLER = "Indic Parler"