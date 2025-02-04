import os
import sys
from pathlib import Path
import aiohttp
import asyncio
import logging
import json
from datetime import datetime
# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'voice_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

async def test_voice_structure():
    """Test to verify the voice API response structure"""
    connector = aiohttp.TCPConnector(ssl=False)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.get('https://127.0.0.1:5000/voices') as response:
                if response.status == 200:
                    data = await response.json()
                    voices = data.get('voices', {})
                    
                    logger.info("\n=== Voice API Response Analysis ===")
                    
                    # Overall structure
                    logger.info(f"\nTop-level keys in response: {list(data.keys())}")
                    logger.info(f"Available voice engines: {list(voices.keys())}")
                    
                    total_voices = 0
                    
                    # Analyze each engine's voices
                    for engine_name, engine_voices in voices.items():
                        logger.info(f"\n--- {engine_name} Engine ---")
                        logger.info(f"Available languages: {list(engine_voices.keys())}")
                        
                        engine_total = sum(len(voice_list) for voice_list in engine_voices.values())
                        total_voices += engine_total
                        
                        logger.info(f"Total voices for {engine_name}: {engine_total}")
                        
                        # Show sample voice structure for each language
                        for language, voice_list in engine_voices.items():
                            if voice_list:
                                logger.info(f"\nLanguage: {language}")
                                logger.info(f"Number of voices: {len(voice_list)}")
                                logger.info(f"Sample voice structure: {json.dumps(voice_list[0], indent=2)}")
                    
                    logger.info(f"\nTotal voices across all engines: {total_voices}")
                    
                    # Verify each voice has required fields
                    logger.info("\n=== Voice Field Validation ===")
                    missing_fields = []
                    required_fields = {'id', 'name', 'language_name', 'engine', 'gender'}
                    
                    for engine_name, engine_voices in voices.items():
                        for language, voice_list in engine_voices.items():
                            for voice in voice_list:
                                missing = required_fields - set(voice.keys())
                                if missing:
                                    missing_fields.append({
                                        'engine': engine_name,
                                        'language': language,
                                        'voice_name': voice.get('name', 'Unknown'),
                                        'missing_fields': list(missing)
                                    })
                    
                    if missing_fields:
                        logger.warning("\nVoices with missing required fields:")
                        for entry in missing_fields:
                            logger.warning(json.dumps(entry, indent=2))
                    else:
                        logger.info("\nAll voices have the required fields")
                    
                else:
                    logger.error(f"Failed to fetch voices: {response.status}")
                    logger.error(await response.text())
        
        except Exception as e:
            logger.error(f"Error testing voice structure: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        asyncio.run(test_voice_structure())
        logger.info("\nVoice structure test completed")
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"\nUnexpected error: {str(e)}")
        raise