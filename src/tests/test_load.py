import os
import sys
from pathlib import Path
import pynvml
# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime
import logging
import torch
import numpy as np
from typing import Dict, List, Optional
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'load_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Test configuration
COMMON_CONFIG = {
    'base_url': 'https://127.0.0.1:5000',
    'test_texts': [
        "This  ",
        "What's up brother? ",
        "Hello, this is a test of the TTS system.",
        "The quick brown fox jumps over the lazy dog.",
        "Testing multiple languages and voices.",
        "This is a longer sentence to test the system's performance with varying text lengths.",
        "Final test message for the TTS pipeline."
    ]
}

# Test configuration profiles
TEST_PROFILES = {
    'stable': {
        'num_users': 100,
        'requests_per_user': 3,
        'timeout': 60,
        'concurrent_requests': 3,
        'request_delay': 1.0,
        'batch_delay': 3.0,
        'gpu_cooldown': 2.0
    },
    'moderate': {
        'num_users': 100,
        'requests_per_user': 3,
        'timeout': 45,
        'concurrent_requests': 5,
        'request_delay': 0.5,
        'batch_delay': 2.0,
        'gpu_cooldown': 1.0
    },
    'aggressive': {
        'num_users': 100,
        'requests_per_user': 3,
        'timeout': 30,
        'concurrent_requests': 8,
        'request_delay': 0.25,
        'batch_delay': 1.0,
        'gpu_cooldown': 0.5
    },
    'progressive': {
        'start_users': 10,
        'max_users': 100,
        'step_size': 10,
        'requests_per_user': 3,
        'timeout': 45,
        'concurrent_requests': 5,
        'request_delay': 0.5,
        'batch_delay': 2.0,
        'gpu_cooldown': 1.0
    }
}

class RealWorldLoadTester:
    def __init__(self, profile_name: str = 'stable'):
        """
        Initialize the load tester with a specific profile.
        
        Args:
            profile_name: Name of the test profile ('stable', 'moderate', 'aggressive', 'progressive')
        """
        # Get the profile configuration
        if profile_name not in TEST_PROFILES:
            logging.warning(f"Profile {profile_name} not found, using 'stable' profile")
            profile_name = 'stable'
        
        self.profile_name = profile_name
        self.config = {**COMMON_CONFIG, **TEST_PROFILES[profile_name]}
        
        # Initialize test parameters from config
        self.base_url = self.config['base_url']
        self.test_texts = self.config['test_texts']
        self.num_users = self.config.get('num_users', 100)
        self.requests_per_user = self.config['requests_per_user']
        self.request_timeout = self.config['timeout']
        self.concurrent_requests = self.config['concurrent_requests']
        self.request_delay = self.config['request_delay']
        self.batch_delay = self.config['batch_delay']
        self.gpu_cooldown = self.config['gpu_cooldown']
        
        # Progressive test parameters
        self.start_users = self.config.get('start_users', 10)
        self.max_users = self.config.get('max_users', 100)
        self.step_size = self.config.get('step_size', 10)
        
        # Initialize counters and results
        self.results = []
        self.success_count = 0
        self.failure_count = 0
        self.total_latency = 0
        self.semaphore = asyncio.Semaphore(self.concurrent_requests)
        
        # Set up logging
        self.logger = self._setup_logging()
        
        self.logger.info(f"Initialized tester with profile: {profile_name}")
        self.logger.info(f"Configuration: {json.dumps(self.config, indent=2)}")

    def _setup_logging(self):
        """Configure logging with detailed formatting"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f'real_world_test_{self.profile_name}_{timestamp}.log'
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
            )
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(stream_handler)
            logger.setLevel(logging.INFO)
        
        return logger

    async def check_gpu_memory(self) -> bool:
        """Check GPU memory usage and perform cleanup if necessary"""
        if not torch.cuda.is_available():
            return True
            
        try:
            gpu_memory_allocated = torch.cuda.memory_allocated()
            gpu_memory_total = torch.cuda.get_device_properties(0).total_memory
            gpu_utilization = gpu_memory_allocated / gpu_memory_total
            
            if gpu_utilization > 0.85:  # 85% threshold
                self.logger.warning(f"High GPU memory utilization: {gpu_utilization:.2%}")
                await self.cleanup_gpu_memory()
                return False
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking GPU memory: {e}")
            return False

    async def cleanup_gpu_memory(self):
        """Clean up GPU memory and wait for cooldown"""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.memory.empty_cache()
            
            import gc
            gc.collect()
            
            await asyncio.sleep(self.gpu_cooldown)
            
        except Exception as e:
            self.logger.error(f"Error during GPU cleanup: {e}")

    async def make_request(self, 
                          session: aiohttp.ClientSession, 
                          voice_id: str,
                          text: str,
                          user_id: int) -> Dict:
        """Make a single TTS request with enhanced error handling and logging"""
        start_time = time.time()
        session_id = f"real_world_test_{user_id}_{int(time.time() * 1000)}"
        
        try:
            # Check GPU memory before request
            while not await self.check_gpu_memory():
                self.logger.info("Waiting for GPU memory to be available...")
                await asyncio.sleep(1)
            
            async with self.semaphore:
                payload = {
                    "text": text,
                    "voice_id": voice_id,
                    "session_id": session_id
                }
                
                self.logger.info(f"Starting request - User {user_id}, Voice {voice_id}, Session {session_id}")
                
                try:
                    async with session.post(
                        f"{self.base_url}/generate-realtime",
                        json=payload,
                        timeout=self.request_timeout,
                        ssl=False
                    ) as response:
                        duration = time.time() - start_time
                        status = response.status
                        
                        # Log raw response for debugging
                        raw_response = await response.text()
                        self.logger.debug(f"Raw response: {raw_response}")
                        
                        try:
                            response_data = json.loads(raw_response)
                        except json.JSONDecodeError as je:
                            self.logger.error(f"JSON decode error: {je}. Raw response: {raw_response}")
                            response_data = {"success": False, "error": f"Invalid JSON response: {raw_response}"}
                        
                        # Create detailed result dictionary
                        result = {
                            'user_id': user_id,
                            'voice_id': voice_id,
                            'session_id': session_id,
                            'text_length': len(text),
                            'latency': duration,
                            'status': status,
                            'raw_status': status,
                            'response_data': response_data,
                            'success': False  # Will be updated below
                        }
                        
                        # Check both HTTP status and response success flag
                        if status == 200:
                            if response_data.get('success', False):
                                result['success'] = True
                                self.success_count += 1
                                self.total_latency += duration
                                self.logger.info(
                                    f"Request successful - User {user_id}, "
                                    f"Session {session_id}, Duration: {duration:.2f}s"
                                )
                            else:
                                self.failure_count += 1
                                error_msg = response_data.get('error', 'No error message in response')
                                result['error'] = f"API reported failure: {error_msg}"
                                self.logger.error(
                                    f"Request failed despite 200 status - User {user_id}, "
                                    f"Session {session_id}: {error_msg}"
                                )
                        else:
                            self.failure_count += 1
                            result['error'] = f"HTTP {status}: {raw_response}"
                            self.logger.error(
                                f"Request failed with status {status} - User {user_id}, "
                                f"Session {session_id}: {raw_response}"
                            )
                        
                        self.results.append(result)
                        await asyncio.sleep(self.request_delay)
                        return result
                        
                except aiohttp.ClientError as ce:
                    error_msg = f"HTTP client error: {str(ce)}"
                    self.logger.error(f"Network error - User {user_id}, Session {session_id}: {error_msg}")
                    raise  # Re-raise for outer try-except
                    
                except asyncio.TimeoutError as te:
                    error_msg = f"Request timeout after {self.request_timeout}s"
                    self.logger.error(f"Timeout - User {user_id}, Session {session_id}: {error_msg}")
                    raise  # Re-raise for outer try-except
                    
        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e) if str(e) else e.__class__.__name__
            self.logger.error(
                f"Request error - User {user_id}, Session {session_id}: "
                f"{error_msg}", exc_info=True
            )
            
            self.failure_count += 1
            
            result = {
                'user_id': user_id,
                'voice_id': voice_id,
                'session_id': session_id,
                'text_length': len(text),
                'latency': duration,
                'status': 500,
                'success': False,
                'error': error_msg,
                'exception_type': e.__class__.__name__,
                'exception_traceback': traceback.format_exc()
            }
            self.results.append(result)
            return result

    async def simulate_user(self, 
                          session: aiohttp.ClientSession,
                          user_id: int,
                          voices: Dict):
        """Simulate a single user making multiple requests"""
        available_voices = []
        
        # Properly extract voice IDs from the voices dictionary
        for engine_voices in voices.values():
            for language_voices in engine_voices.values():
                for voice in language_voices:
                    # Handle both VoiceInfo objects and dictionaries
                    voice_id = voice.id if hasattr(voice, 'id') else voice['id']
                    available_voices.append(voice_id)
        
        if not available_voices:
            self.logger.error(f"No voices available for user {user_id}")
            return
        
        for i in range(self.requests_per_user):
            voice_id = random.choice(available_voices)
            text = random.choice(self.test_texts)
            
            # Extract language code from voice_id for XTTS voices
            if voice_id.startswith('xtts_'):
                # voice_id format is 'xtts_lang_gender'
                # we need the language code part
                lang_code = voice_id.split('_')[1]
                
                try:
                    await self.make_request(session, voice_id, text, user_id)
                except Exception as e:
                    self.logger.error(f"Request error for user {user_id} with voice {voice_id}: {str(e)}")
            else:
                # For non-XTTS voices, proceed as normal
                try:
                    await self.make_request(session, voice_id, text, user_id)
                except Exception as e:
                    self.logger.error(f"Request error for user {user_id} with voice {voice_id}: {str(e)}")
        
        # Clear session after requests
        try:
            session_id = f"real_world_test_{user_id}"
            async with session.post(
                f"{self.base_url}/clear-session",
                json={"session_id": session_id}
            ) as response:
                if response.status != 200:
                    self.logger.warning(f"Failed to clear session for user {user_id}")
        except Exception as e:
            self.logger.warning(f"Error clearing session for user {user_id}: {str(e)}")


    async def run_test(self) -> Dict:
        """Run the load test according to the selected profile"""
        if self.profile_name == 'progressive':
            return await self.run_progressive_test()
        else:
            return await self.run_standard_test(self.num_users)

    async def run_standard_test(self, num_users: int) -> Dict:
        """Run a standard load test with fixed number of users"""
        start_time = time.time()
        self.logger.info(f"Starting test with {num_users} users")
        
        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Fetch voices
            try:
                async with session.get(f"{self.base_url}/voices") as response:
                    if response.status != 200:
                        raise Exception(f"Failed to fetch voices: {response.status}")
                    voices = (await response.json()).get('voices', {})
            except Exception as e:
                self.logger.error(f"Error fetching voices: {e}")
                return None
            
            # Process users in batches
            batch_size = self.concurrent_requests
            for batch_start in range(0, num_users, batch_size):
                batch_end = min(batch_start + batch_size, num_users)
                self.logger.info(f"Processing users {batch_start} to {batch_end-1}")
                
                user_tasks = []
                for user_id in range(batch_start, batch_end):
                    user_tasks.append(self.simulate_user(session, user_id, voices))
                
                await asyncio.gather(*user_tasks)
                await asyncio.sleep(self.batch_delay)
        
        return self._generate_summary(start_time)

    async def run_progressive_test(self) -> Dict:
        """Run a progressive test, increasing users gradually"""
        overall_start_time = time.time()
        overall_results = []
        summaries = []
        
        for num_users in range(self.start_users, self.max_users + 1, self.step_size):
            self.logger.info(f"\n=== Testing with {num_users} users ===")
            
            # Reset counters for this iteration
            self.success_count = 0
            self.failure_count = 0
            self.total_latency = 0
            
            # Run test with current number of users
            summary = await self.run_standard_test(num_users)
            
            if summary:
                summary['num_users'] = num_users
                summaries.append(summary)
                overall_results.extend(self.results)
                
                # Check error rate
                error_rate = summary['failed_requests'] / summary['total_requests']
                if error_rate > 0.1:  # More than 10% errors
                    self.logger.warning(f"High error rate ({error_rate:.2%}) detected. Stopping progression.")
                    break
            
            await asyncio.sleep(5)  # Cool-down between iterations
        
        return self._generate_progressive_summary(overall_start_time, summaries)

    def _generate_summary(self, start_time: float) -> Dict:
        """Generate summary statistics for the test"""
        total_time = time.time() - start_time
        total_requests = self.success_count + self.failure_count
        avg_latency = self.total_latency / self.success_count if self.success_count > 0 else 0
        
        summary = {
            'profile': self.profile_name,
            'total_time': total_time,
            'total_requests': total_requests,
            'successful_requests': self.success_count,
            'failed_requests': self.failure_count,
            'average_latency': avg_latency,
            'requests_per_second': total_requests / total_time if total_time > 0 else 0
        }
        
        self._log_summary(summary)
        return summary

    def _generate_progressive_summary(self, start_time: float, summaries: List[Dict]) -> Dict:
        """Generate summary for progressive test"""
        return {
            'profile': 'progressive',
            'total_time': time.time() - start_time,
            'total_requests': sum(s['total_requests'] for s in summaries),
            'successful_requests': sum(s['successful_requests'] for s in summaries),
            'failed_requests': sum(s['failed_requests'] for s in summaries),
            'average_latency': sum(s['average_latency'] for s in summaries) / len(summaries),
            'max_stable_users': summaries[-1]['num_users'],
            'summaries_per_step': summaries
        }

    def _log_summary(self, summary: Dict):
        """Log test summary"""
        self.logger.info("\n=== Test Summary ===")
        self.logger.info(f"Profile: {summary['profile']}")
        self.logger.info(f"Total Time: {summary['total_time']:.2f} seconds")
        self.logger.info(f"Total Requests: {summary['total_requests']}")
        self.logger.info(f"Successful Requests: {summary['successful_requests']}")
        self.logger.info(f"Failed Requests: {summary['failed_requests']}")
        self.logger.info(f"Average Latency: {summary['average_latency']:.2f} seconds")
        self.logger.info(f"Requests per Second: {summary['requests_per_second']:.2f}")

    def save_results(self, summary: Dict):
        """Save test results to a file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path.cwd() / 'test_results'
        output_dir.mkdir(exist_ok=True)
        
        output_file = output_dir / f'real_world_test_{self.profile_name}_{timestamp}.json'
        
        with open(output_file, 'w') as f:
            json.dump({
                'summary': summary,
                'results': self.results,
                'config': self.config,
            }, f, indent=2)
        
        self.logger.info(f"Results saved to: {output_file}")

def save_results(summary, results, profile_name):
    """Save test results to a file"""
    output_dir = Path.cwd() / 'test_results'
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'load_test_results_{timestamp}.json'
    
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'results': results,
            'config': TEST_PROFILES[profile_name],
        }, f, indent=2)
    
    logger.info(f"Results saved to: {output_file}")

async def main():
    # Choose a profile: 'stable', 'moderate', 'aggressive', or 'progressive'
    tester = RealWorldLoadTester(profile_name='moderate')
    
    summary = await tester.run_test()
    tester.save_results(summary)

if __name__ == "__main__":
    asyncio.run(main())