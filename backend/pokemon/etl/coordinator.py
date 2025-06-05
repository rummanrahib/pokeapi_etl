import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from .extractors import PokeAPIExtractor
from .loaders import LoaderError, PokemonDataLoader
from .transformers import PokemonDataTransformer, TransformationError

logger = logging.getLogger(__name__)

@dataclass
class ETLStats:
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    failed_ids: Set[int] = None
    
    def __post_init__(self):
        self.failed_ids = set()
    
    def record_success(self):
        self.total_processed += 1
        self.successful += 1
    
    def record_failure(self, pokemon_id: int):
        self.total_processed += 1
        self.failed += 1
        self.failed_ids.add(pokemon_id)

class ETLError(Exception):
    pass

class PokemonETLCoordinator:
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self):
        self.transformer = PokemonDataTransformer()
        self.loader = PokemonDataLoader()
        self.stats = ETLStats()
    
    def process_pokemon(
        self,
        limit: Optional[int] = None,
        batch_size: int = 20,
        max_workers: int = 4,
        retry_failed: bool = True
    ) -> ETLStats:
        start_time = time.time()
        
        try:
            with PokeAPIExtractor() as extractor:
                pokemon_list = extractor.get_all_pokemon(limit=limit)
                total_pokemon = len(pokemon_list)
                
                logger.info(
                    f"Starting to process {total_pokemon} Pokemon "
                    f"with batch size {batch_size}"
                )
                
                # processing batches in parallel
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # submit batch processing tasks
                    futures = [
                        executor.submit(
                            self._process_batch,
                            extractor,
                            pokemon_list[i:i + batch_size],
                            i // batch_size + 1
                        )
                        for i in range(0, total_pokemon, batch_size)
                    ]
                    
                    # awaiting all batches to complete
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            logger.error(f"Batch processing failed: {e}")
                
                # retrying failed Pokemon if flag is set to true
                if retry_failed and self.stats.failed_ids:
                    self._retry_failed_pokemon(extractor)
                
                # log statistics
                duration = time.time() - start_time
                self._log_completion_stats(duration)
                
                return self.stats
                
        except Exception as e:
            logger.error(f"Critical error in Pokemon ETL process: {e}")
            raise ETLError(f"ETL process failed: {str(e)}")
            
        finally:
            self.loader.clear_caches()
    
    def _process_batch(
        self,
        extractor: PokeAPIExtractor,
        batch: List[Dict[str, Any]],
        batch_num: int
    ) -> None:
        logger.info(f"Starting batch {batch_num} with {len(batch)} Pokemon")
        batch_start = time.time()
        
        for pokemon_entry in batch:
            pokemon_id = self._extract_pokemon_id(pokemon_entry)
            if not pokemon_id:
                continue
            
            try:
                self._process_single_pokemon(extractor, pokemon_id, pokemon_entry['name'])
                self.stats.record_success()
                
            except Exception as e:
                logger.error(
                    f"Failed to process Pokemon {pokemon_entry['name']} "
                    f"(ID: {pokemon_id}): {e}"
                )
                self.stats.record_failure(pokemon_id)
        
        batch_duration = time.time() - batch_start
        logger.info(f"Completed batch {batch_num} in {batch_duration:.2f} seconds")
    
    def _process_single_pokemon(
        self,
        extractor: PokeAPIExtractor,
        pokemon_id: int,
        pokemon_name: str,
        retry_count: int = 0
    ) -> None:
        try:
            raw_data = extractor.get_pokemon_data(pokemon_id)
            transformed_data = self.transformer.transform_complete_pokemon_data(raw_data)
            self.loader.load_complete_pokemon_data(transformed_data)
            
            logger.info(f"Successfully processed Pokemon: {pokemon_name}")
            
        except (TransformationError, LoaderError) as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    f"Retrying Pokemon {pokemon_name} "
                    f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                )
                time.sleep(self.RETRY_DELAY * (retry_count + 1))
                self._process_single_pokemon(
                    extractor,
                    pokemon_id,
                    pokemon_name,
                    retry_count + 1
                )
            else:
                raise
    
    def _retry_failed_pokemon(self, extractor: PokeAPIExtractor) -> None:
        if not self.stats.failed_ids:
            return
        
        logger.info(f"Retrying {len(self.stats.failed_ids)} failed Pokemon")
        
        # reset failed stats for retry
        failed_ids = self.stats.failed_ids.copy()
        self.stats.failed_ids.clear()
        self.stats.failed = 0
        
        for pokemon_id in failed_ids:
            try:
                pokemon_data = extractor.get_pokemon_data(pokemon_id)
                pokemon_name = pokemon_data['pokemon']['name']
                
                # process with fresh retry
                self._process_single_pokemon(extractor, pokemon_id, pokemon_name)
                self.stats.record_success()
                
            except Exception as e:
                logger.error(f"Retry failed for Pokemon ID {pokemon_id}: {e}")
                self.stats.record_failure(pokemon_id)
    
    def _extract_pokemon_id(self, pokemon_entry: Dict[str, Any]) -> Optional[int]:
        try:
            return int(pokemon_entry['url'].split('/')[-2])
        except (KeyError, ValueError, IndexError) as e:
            logger.error(f"Failed to extract Pokemon ID from entry: {e}")
            return None
    
    def _log_completion_stats(self, duration: float) -> None:
        logger.info(
            f"\nETL Process Completed:"
            f"\n- Total Processed: {self.stats.total_processed}"
            f"\n- Successful: {self.stats.successful}"
            f"\n- Failed: {self.stats.failed}"
            f"\n- Duration: {duration:.2f} seconds"
            f"\n- Average Time Per Pokemon: {duration/self.stats.total_processed:.2f} seconds"
        )
        
        if self.stats.failed_ids:
            logger.warning(f"Failed Pokemon IDs: {sorted(self.stats.failed_ids)}") 