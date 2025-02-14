# src/core/cuda_monitor.py
import torch
import signal
import logging
import sys
import os
from typing import Optional
from datetime import datetime

class CudaMonitor:
    def __init__(self, restart_script_path: Optional[str] = r"C:\Users\Cihan\Desktop\NeviTechTTS\src\docker-restart.sh"):
        self.logger = logging.getLogger(__name__)
        self.restart_script = restart_script_path
        self.cuda_errors = 0
        self.max_errors = 3  # Maximum number of CUDA errors before forcing restart
        self.error_timeout = 300  # 5 minutes between error resets
        self.last_error_time = None
        # Set up signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
    def check_cuda(self) -> bool:
        """Check if CUDA is working properly"""
        try:
            if not torch.cuda.is_available():
                return False
                
            # Try a simple CUDA operation
            test_tensor = torch.cuda.FloatTensor(2, 2).fill_(1.0)
            result = torch.matmul(test_tensor, test_tensor)
            del test_tensor
            del result
            torch.cuda.empty_cache()
            
            return True
            
        except Exception as e:
            self.logger.error(f"CUDA error detected: {str(e)}")
            return False
            
    def handle_cuda_error(self):
        """Handle CUDA errors and trigger restart if needed"""
        current_time = datetime.now()
        
        # Reset error count if enough time has passed
        if self.last_error_time and (current_time - self.last_error_time).total_seconds() > self.error_timeout:
            self.cuda_errors = 0
            
        self.cuda_errors += 1
        self.last_error_time = current_time
        
        self.logger.warning(f"CUDA error count: {self.cuda_errors}")
        
        if self.cuda_errors >= self.max_errors:
            self.logger.error("Maximum CUDA errors reached, initiating container restart")
            self.restart_container()
            
    def restart_container(self):
        """Trigger container restart"""
        try:
            if os.path.exists(self.restart_script):
                self.logger.info("Executing restart script")
                os.system(f"bash {self.restart_script}")
            else:
                self.logger.error(f"Restart script not found at {self.restart_script}")
                # Exit with error code 1 to trigger Docker's restart policy
                sys.exit(1)
                
        except Exception as e:
            self.logger.error(f"Error during restart: {str(e)}")
            sys.exit(1)
            
    def handle_shutdown(self, signum, frame):
        """Clean shutdown handler"""
        self.logger.info("Received shutdown signal, cleaning up...")
        torch.cuda.empty_cache()
        sys.exit(0)
