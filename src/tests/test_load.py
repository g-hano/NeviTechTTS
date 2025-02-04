import os
import sys
from pathlib import Path

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
TEST_CONFIG = {
    'num_users': 100,
    'requests_per_user': 3,
    'base_url': 'https://127.0.0.1:5000',
    'test_texts': [
        "This  ",
        "What's up brother? ",
        "Hello, this is a test of the TTS system.",
        "The quick brown fox jumps over the lazy dog.",
        "Testing multiple languages and voices.",
        "This is a longer sentence to test the system's performance with varying text lengths.",
        "Final test message for the TTS pipeline."
    ],
    'timeout': 60,  # Increased timeout
    'concurrent_requests': 3,  # Reduced from 5
    'request_delay': 1.0,  # Increased from 0.5
    'batch_delay': 3.0,  # Delay between batches
    'gpu_cooldown': 2.0  # Delay after each generation
}

class TTSLoadTester:
    def __init__(self, config):
        self.config = config
        self.results = []
        self.success_count = 0
        self.failure_count = 0
        self.total_latency = 0
        self.semaphore = asyncio.Semaphore(config['concurrent_requests'])

    def create_client_session(self):
        """Create a client session with SSL verification disabled"""
        connector = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=self.config['timeout'])
        return aiohttp.ClientSession(connector=connector, timeout=timeout)

    def extract_voice_ids(self, voices):
        """Extract voice IDs from the voice data structure"""
        available_voices = []
        try:
            for engine_name, engine_voices in voices.items():
                logger.info(f"Processing voices for engine: {engine_name}")
                for language, voice_list in engine_voices.items():
                    for voice in voice_list:
                        if isinstance(voice, dict) and 'id' in voice:
                            available_voices.append(voice['id'])
                            
            logger.info(f"Found {len(available_voices)} available voices")
            if available_voices:
                logger.info(f"Sample voice IDs: {available_voices[:5]}")
            return available_voices
        except Exception as e:
            logger.error(f"Error extracting voice IDs: {str(e)}")
            logger.error(f"Voice data structure: {json.dumps(voices, indent=2)}")
            return []

    async def simulate_user(self, user_id: int, voices: dict):
        """Simulate a single user making multiple requests"""
        async with self.create_client_session() as session:
            available_voices = []
            for engine_voices in voices.values():
                for language_voices in engine_voices.values():
                    for voice in language_voices:
                        if isinstance(voice, dict) and 'id' in voice:
                            available_voices.append(voice['id'])
            
            if not available_voices:
                logger.error(f"No voices available for user {user_id}")
                return
            
            logger.info(f"User {user_id} starting requests with {len(available_voices)} available voices")
            
            for request_num in range(self.config['requests_per_user']):
                voice_id = random.choice(available_voices)
                text = random.choice(self.config['test_texts'])
                
                async with self.semaphore:  # Limit concurrent requests
                    logger.debug(f"User {user_id} making request {request_num + 1}/{self.config['requests_per_user']} with voice {voice_id}")
                    await self.generate_speech(session, user_id, voice_id, text)
                    await asyncio.sleep(self.config['request_delay'])  # Use configured delay

            # Clear session after user is done
            try:
                session_id = f"loadtest_{user_id}"
                async with session.post(
                    f"{self.config['base_url']}/clear-session",
                    json={"session_id": session_id}
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to clear session for user {user_id}")
            except Exception as e:
                logger.warning(f"Error clearing session for user {user_id}: {str(e)}")

    async def generate_speech(self, session, user_id: int, voice_id: str, text: str):
        """Generate speech using the TTS service"""
        start_time = time.time()
        try:
            session_id = f"loadtest_{user_id}_{int(time.time() * 1000)}"
            
            payload = {
                "text": text,
                "voice_id": voice_id,
                "session_id": session_id
            }
            
            url = f"{self.config['base_url']}/generate-realtime"
            
            logger.debug(f"Making request to {url} with voice_id: {voice_id}, session_id: {session_id}")
            
            async with session.post(url, json=payload) as response:
                duration = time.time() - start_time
                status = response.status
                
                try:
                    response_data = await response.json()
                except:
                    response_data = await response.text()
                
                result = {
                    'user_id': user_id,
                    'voice_id': voice_id,
                    'session_id': session_id,
                    'text_length': len(text),
                    'latency': duration,
                    'status': status,
                    'success': status == 200 and response_data.get('success', False)
                }
                
                if result['success']:
                    self.success_count += 1
                    self.total_latency += duration
                    logger.debug(f"User {user_id}: Successfully generated speech")
                else:
                    self.failure_count += 1
                    result['error'] = response_data if isinstance(response_data, str) else json.dumps(response_data)
                    logger.error(f"Request failed - User {user_id}: Status {status}, Response: {result['error']}")
                    logger.error(f"Failed request details - Voice ID: {voice_id}, Session ID: {session_id}, Text: {text}")
                
                self.results.append(result)
                
                # Add GPU cooldown period after each generation
                await asyncio.sleep(self.config['gpu_cooldown'])
                
                return result
                
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in generate_speech - User {user_id}: {str(e)}")
            logger.error(f"Request details - Voice ID: {voice_id}, Text: {text}")
            self.failure_count += 1
            result = {
                'user_id': user_id,
                'voice_id': voice_id,
                'text_length': len(text),
                'latency': duration,
                'status': 500,
                'success': False,
                'error': str(e)
            }
            self.results.append(result)
            
            # Add GPU cooldown period even after errors
            await asyncio.sleep(self.config['gpu_cooldown'])
            
            return result
        
    async def check_server_availability(self):
        """Check if the server is available before starting the test"""
        try:
            async with self.create_client_session() as session:
                async with session.get(f"{self.config['base_url']}/voices") as response:
                    if response.status == 200:
                        logger.info("Server is available and responding")
                        return True
                    else:
                        logger.error(f"Server returned status code: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error response: {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Cannot connect to server: {str(e)}")
            logger.error(f"Please make sure the server is running at {self.config['base_url']}")
            return False

    async def fetch_voices(self, session):
        """Fetch available voices from the TTS service"""
        try:
            async with session.get(f"{self.config['base_url']}/voices") as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, dict):
                        logger.error(f"Unexpected voices response format: {data}")
                        return {}
                        
                    voices = data.get('voices', {})
                    total_voices = sum(
                        len(voice_list) 
                        for engine_voices in voices.values() 
                        for voice_list in engine_voices.values()
                    )
                    logger.info(f"Successfully fetched {total_voices} voices")
                    return voices
                else:
                    logger.error(f"Failed to fetch voices: {response.status}")
                    error_text = await response.text()
                    logger.error(f"Error response: {error_text}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching voices: {e}")
            return {}

    async def run_load_test(self):
        """Run the load test with multiple concurrent users"""
        try:
            if not await self.check_server_availability():
                logger.error("Server is not available. Aborting test.")
                return None, None

            start_time = time.time()
            logger.info("Starting load test...")
            
            async with self.create_client_session() as session:
                voices = await self.fetch_voices(session)
                if not voices:
                    logger.error("Failed to fetch voices. Aborting test.")
                    return None, None
                
                logger.info(f"Successfully fetched voices. Starting test with {self.config['num_users']} users")
                
                batch_size = self.config['concurrent_requests']
                num_batches = (self.config['num_users'] + batch_size - 1) // batch_size
                
                try:
                    for batch_num in range(num_batches):
                        start_idx = batch_num * batch_size
                        end_idx = min((batch_num + 1) * batch_size, self.config['num_users'])
                        
                        logger.info(f"Processing batch {batch_num + 1}/{num_batches} (users {start_idx} to {end_idx-1})")
                        
                        batch_tasks = []
                        for user_id in range(start_idx, end_idx):
                            batch_tasks.append(self.simulate_user(user_id, voices))
                        
                        # Run batch of users
                        await asyncio.gather(*batch_tasks)
                        
                        # Add delay between batches
                        if batch_num < num_batches - 1:
                            logger.info(f"Batch completed. Cooling down for {self.config['batch_delay']} seconds...")
                            await asyncio.sleep(self.config['batch_delay'])
                    
                    # Calculate final results
                    total_time = time.time() - start_time
                    total_requests = self.success_count + self.failure_count
                    avg_latency = self.total_latency / self.success_count if self.success_count > 0 else 0
                    
                    summary = {
                        'total_time': total_time,
                        'total_requests': total_requests,
                        'successful_requests': self.success_count,
                        'failed_requests': self.failure_count,
                        'average_latency': avg_latency,
                        'requests_per_second': total_requests / total_time if total_time > 0 else 0,
                        'batches': num_batches,
                        'batch_size': batch_size
                    }
                    
                    logger.info("\n=== Load Test Summary ===")
                    logger.info(f"Total Time: {total_time:.2f} seconds")
                    logger.info(f"Total Requests: {total_requests}")
                    logger.info(f"Successful Requests: {self.success_count}")
                    logger.info(f"Failed Requests: {self.failure_count}")
                    logger.info(f"Average Latency: {avg_latency:.2f} seconds")
                    logger.info(f"Requests per Second: {total_requests / total_time:.2f}")
                    logger.info(f"Number of Batches: {num_batches}")
                    logger.info(f"Batch Size: {batch_size}")
                    
                    return summary, self.results

                except Exception as e:
                    logger.error(f"Error during batch processing: {str(e)}")
                    raise

        except Exception as e:
            logger.error(f"Error during load test: {str(e)}")
            if hasattr(self, 'success_count') and hasattr(self, 'failure_count'):
                total_time = time.time() - start_time
                total_requests = self.success_count + self.failure_count
                avg_latency = self.total_latency / self.success_count if self.success_count > 0 else 0
                
                # Create partial summary even if test didn't complete
                summary = {
                    'total_time': total_time,
                    'total_requests': total_requests,
                    'successful_requests': self.success_count,
                    'failed_requests': self.failure_count,
                    'average_latency': avg_latency,
                    'requests_per_second': total_requests / total_time if total_time > 0 else 0,
                    'error': str(e),
                    'completed': False
                }
                
                return summary, self.results
                
            return None, None

def save_results(summary, results):
    """Save test results to a file"""
    output_dir = Path.cwd() / 'test_results'
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f'load_test_results_{timestamp}.json'
    
    with open(output_file, 'w') as f:
        json.dump({
            'summary': summary,
            'results': results,
            'config': TEST_CONFIG
        }, f, indent=2)
    
    logger.info(f"Results saved to: {output_file}")

async def main():
    logger.info("Starting TTS Load Test...")
    logger.info(f"Configuration: {TEST_CONFIG}")
    
    try:
        tester = TTSLoadTester(TEST_CONFIG)
        summary, results = await tester.run_load_test()
        
        if summary is not None and results is not None:
            save_results(summary, results)
            logger.info("Load test completed and results saved.")
        else:
            logger.error("Test failed to complete successfully")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        logger.info("Load test finished.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise