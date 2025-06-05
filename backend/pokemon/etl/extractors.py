import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')

def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    @wraps(func)
    def wrapper(self, *args, **kwargs) -> T:
        for attempt in range(self.MAX_RETRIES):
            try:
                if attempt > 0:
                    time.sleep(self.RETRY_DELAY * attempt)
                return func(self, *args, **kwargs)
            except httpx.HTTPError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying...")
    return wrapper

class PokeAPIExtractor:
    # NOTE: BASE_URL kept hardcoded for now
    BASE_URL = "https://pokeapi.co/api/v2"
    ENDPOINTS = {
        'pokemon': f"{BASE_URL}/pokemon",
        'species': f"{BASE_URL}/pokemon-species",
        'evolution': f"{BASE_URL}/evolution-chain",
        'move': f"{BASE_URL}/move"
    }
    
    # configuration
    RATE_LIMIT_DELAY = 0.1  # ms between requests
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    REQUEST_TIMEOUT = 30  # seconds
    
    def __init__(self):
        self.client = httpx.Client(
            timeout=self.REQUEST_TIMEOUT,
            headers={
                "User-Agent": "Pokemon ETL Pipeline/1.0",
                "Accept": "application/json"
            }
        )
        self._last_request_time = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
    
    def _extract_id(self, url: str) -> Optional[int]:
        try:
            path = urlparse(url).path.rstrip('/').split('/')
            return int(path[-1])
        except (ValueError, IndexError):
            logger.error(f"Failed to extract ID from URL: {url}")
            return None
    
    @with_retry
    def _make_request(self, url: str) -> Dict[str, Any]:
        try:
            current_time = time.time()
            time_since_last = current_time - self._last_request_time
            if time_since_last < self.RATE_LIMIT_DELAY:
                time.sleep(self.RATE_LIMIT_DELAY - time_since_last)
            
            response = self.client.get(url)
            response.raise_for_status()
            self._last_request_time = time.time()
            
            return response.json()
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    def get_all_pokemon(self, limit: Optional[int] = 5) -> List[Dict[str, Any]]:
        try:
            params = {"limit": limit}
            data = self._make_request(f"{self.ENDPOINTS['pokemon']}?{httpx.QueryParams(params)}")
            return data['results']
        except Exception as e:
            logger.error(f"Failed to get Pokemon list: {str(e)}")
            raise
    
    def get_pokemon_data(self, pokemon_id: int) -> Dict[str, Any]:
        try:
            logger.info(f"Fetching data for Pokemon #{pokemon_id}")
            
            pokemon_data = self._make_request(f"{self.ENDPOINTS['pokemon']}/{pokemon_id}")
            species_data = self._make_request(f"{self.ENDPOINTS['species']}/{pokemon_id}")
            
            evolution_url = species_data['evolution_chain']['url']
            evolution_id = self._extract_id(evolution_url)
            if not evolution_id:
                raise ValueError(f"Invalid evolution chain URL: {evolution_url}")
            
            evolution_data = self._make_request(f"{self.ENDPOINTS['evolution']}/{evolution_id}")
            # move details (with batch processing)
            moves_data = self._get_move_details(pokemon_data.get('moves', []))
            
            return {
                'pokemon': pokemon_data,
                'species': species_data,
                'evolution_chain': evolution_data,
                'moves': moves_data
            }
            
        except Exception as e:
            logger.error(f"Failed to get Pokemon #{pokemon_id} data: {str(e)}")
            raise
    
    def _get_move_details(self, moves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # just the first move for now
        try:
            if moves:
                move = moves[0]
                move_id = self._extract_id(move['move']['url'])
                if move_id:
                    move_detail = self._make_request(f"{self.ENDPOINTS['move']}/{move_id}")
                    return [{
                        'move': move_detail,
                        'learn_details': move['version_group_details']
                    }]
            return []
        except Exception as e:
            logger.error(f"Error fetching move data: {str(e)}")
            return []