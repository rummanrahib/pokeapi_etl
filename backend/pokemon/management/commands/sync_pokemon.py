import logging
import sys
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from ...etl.coordinator import ETLError, ETLStats, PokemonETLCoordinator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Synchronize and ETL Pokemon data from PokeAPI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            help='Number of Pokemon to synchronize (default: all)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=20,
            help='Number of Pokemon to process in each batch (default: 20)'
        )
        parser.add_argument(
            '--workers',
            type=int,
            default=4,
            help='Number of parallel workers (default: 4)'
        )
        parser.add_argument(
            '--skip-retry',
            action='store_true',
            help='Skip retrying failed Pokemon'
        )
        parser.add_argument(
            '--start-from',
            type=int,
            help='Start synchronization from this Pokemon ID'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update existing Pokemon data'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information'
        )
    
    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        try:
            self._configure_logging(options['verbose'])
            self._show_configuration(options)
            
            coordinator = PokemonETLCoordinator()
            stats = coordinator.process_pokemon(
                limit=options['limit'],
                batch_size=options['batch_size'],
                max_workers=options['workers'],
                retry_failed=not options['skip_retry']
            )
            
            self._show_results(stats)
            
            return self.style.SUCCESS('Pokemon data synchronization completed successfully!')
        except ETLError as e:
            logger.error(f'ETL process failed: {e}')
            raise CommandError(f'Synchronization failed: {e}')
            
        except Exception as e:
            logger.error(f'Unexpected error: {e}', exc_info=True)
            raise CommandError(f'Unexpected error: {e}')
            
        finally:
            connection.close()
    
    def _configure_logging(self, verbose: bool) -> None:
        log_level = logging.DEBUG if verbose else logging.INFO
        
        # configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # console handler
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
    
    def _show_configuration(self, options: dict) -> None:
        config_msg = '\nConfiguration:'
        config_msg += f"\n- Limit: {options['limit'] or 20}"
        config_msg += f"\n- Batch Size: {options['batch_size']}"
        config_msg += f"\n- Workers: {options['workers']}"
        config_msg += f"\n- Retry on Failed: {not options['skip_retry']}"
        config_msg += f"\n- Start From: {options['start_from'] or 'Beginning'}"
        config_msg += f"\n- Force Update: {options['force']}"
        config_msg += f"\n- Verbose: {options['verbose']}"
        
        self.stdout.write(self.style.SUCCESS(config_msg))
    
    def _show_results(self, stats: ETLStats) -> None:
        success_rate = (stats.successful / stats.total_processed * 100) if stats.total_processed > 0 else 0
        
        # build results message
        results_msg = '\nResults:'
        results_msg += f'\n- Total Processed: {stats.total_processed}'
        results_msg += f'\n- Successful: {stats.successful}'
        results_msg += f'\n- Failed: {stats.failed}'
        results_msg += f'\n- Success Rate: {success_rate:.2f}%'
        
        if stats.failed_ids:
            results_msg += f'\n- Failed Pokemon IDs: {sorted(stats.failed_ids)}'
        
        if success_rate == 100:
            self.stdout.write(self.style.SUCCESS(results_msg))
        elif success_rate >= 90:
            self.stdout.write(self.style.WARNING(results_msg))
        else:
            self.stdout.write(self.style.ERROR(results_msg)) 