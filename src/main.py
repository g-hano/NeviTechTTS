# src/main.py
from flask import Flask
from flask_cors import CORS
import logging
import ssl

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.ConfigLoader import ConfigLoader
from core.tts_manager import TTSManager
from api.routes import register_routes
from core.cuda_monitor import CudaMonitor

def create_app(config_path: str):
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}})

    cuda_monitor = CudaMonitor(r"C:\Users\Cihan\Desktop\NeviTechTTS\src\docker-restart.sh")

    if not cuda_monitor.check_cuda():
        logging.error("Initial CUDA check failed")
        cuda_monitor.handle_cuda_error()

    # Load configuration
    config = ConfigLoader.load_config(config_path)
    ConfigLoader.ensure_directories(config)
    
    # Initialize TTS Manager
    tts_manager = TTSManager(config)
    
    # Register routes
    register_routes(app, tts_manager)
    
    return app, config

def setup_logging(base_dir):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(base_dir, 'app.log'))
        ]
    )

def main():
    config_path = "src/config.yaml"
    app, config = create_app(config_path)
    
    try:
        context = None
        if os.path.exists(config.paths.cert_path) and os.path.exists(config.paths.key_path):
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(config.paths.cert_path, config.paths.key_path)
        
        app.run(
            host=config.flask.host,
            port=config.flask.port,
            ssl_context=context
        )
    except Exception as e:
        logging.error(f"Server Error: {e}")
        app.run(
            host=config.flask.host,
            port=config.flask.port
        )

if __name__ == "__main__":
    main()
