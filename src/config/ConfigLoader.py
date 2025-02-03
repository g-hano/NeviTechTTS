import yaml
import os
from dataclasses import dataclass
from typing import Dict
from pathlib import Path
import logging

@dataclass
class CleanupConfig:
    max_age_hours: int = 24
    min_free_space_mb: int = 1000
    cleanup_interval_minutes: int = 30

@dataclass
class ModelConfig:
    xtts_base_model: str
    xtts_vietnamese: str
    indic_model: str

@dataclass
class DirectoryConfig:
    audio_output_dir: str
    vietnamese_model_dir: str

@dataclass
class PathConfig:
    key_path: str
    cert_path: str
    google_credentials: str

@dataclass
class FlaskConfig:
    port: int
    host: str

@dataclass
class ReferenceAudioConfig:
    male: str
    female: str

@dataclass
class AppConfig:
    models: ModelConfig
    directories: DirectoryConfig
    paths: PathConfig
    flask: FlaskConfig
    reference_audio_paths: ReferenceAudioConfig
    kokoro_speed: float
    cleanup: CleanupConfig

class ConfigLoader:
    @staticmethod
    def load_config(config_path: str = "config.yaml") -> AppConfig:
        with open(config_path, 'r') as file:
            config_dict = yaml.safe_load(file)

        return AppConfig(
            models=ModelConfig(**config_dict['models']),
            directories=DirectoryConfig(**config_dict['directories']),
            paths=PathConfig(**config_dict['paths']),
            flask=FlaskConfig(**config_dict['flask']),
            reference_audio_paths=ReferenceAudioConfig(**config_dict['reference_audio_paths']),
            kokoro_speed=config_dict['kokoro_speed'],
            cleanup=CleanupConfig(**config_dict.get('cleanup', {}))  # Use defaults if not specified
        
        )

    @staticmethod
    def ensure_directories(config: AppConfig):
        """
        Ensure all required directories exist.
        Uses Path for better path handling and adds logging.
        """
        logger = logging.getLogger(__name__)
        
        # Get the base directory (where the application is running)
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        directories = {
            'audio_output': base_dir / config.directories.audio_output_dir,
            'vietnamese_model': base_dir / config.directories.vietnamese_model_dir
        }
        
        for name, path in directories.items():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Ensured directory exists: {path}")
            except Exception as e:
                logger.error(f"Failed to create directory {name} at {path}: {e}")
                raise RuntimeError(f"Failed to create required directory: {name}") from e
        
        # Verify directories exist and are writable
        for name, path in directories.items():
            if not path.exists():
                raise RuntimeError(f"Directory {name} at {path} was not created successfully")
            if not os.access(path, os.W_OK):
                raise RuntimeError(f"Directory {name} at {path} is not writable")
            
        logger.info("All required directories have been created and verified")