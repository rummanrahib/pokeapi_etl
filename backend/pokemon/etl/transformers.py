import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class TransformationError(Exception):
    message: str
    data: Dict[str, Any]
    field: Optional[str] = None

# PokemonDataTransformer: transforms PokeAPI data to match Django models
class PokemonDataTransformer:
    REQUIRED_POKEMON_FIELDS = {
        'id': int,
        'name': str,
        'height': int,
        'weight': int,
        'stats': list,
    }
    
    REQUIRED_STATS = [
        'hp', 'attack', 'defense',
        'special-attack', 'special-defense', 'speed'
    ]
    
    def transform_complete_pokemon_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self._validate_raw_data(raw_data)
            
            pokemon_data = self._transform_pokemon(raw_data['pokemon'])
            species_data = self._transform_species(raw_data['species'])
            evolution_data = self._transform_evolution_chain(raw_data['evolution_chain'])
            moves_data = self._transform_moves(raw_data['moves'])
            
            transformed_data = {
                'pokemon': pokemon_data,
                'species': species_data,
                'evolution_chain': evolution_data,
                'moves': moves_data
            }
            
            logger.info(f"Successfully transformed data for Pokemon: {pokemon_data['name']}")
            return transformed_data
            
        except TransformationError as e:
            logger.error(f"Transformation error in {e.field}: {e.message}")
            raise
        
        except Exception as e:
            logger.error(f"Unexpected error transforming Pokemon data: {e}")
            raise TransformationError(message=str(e), data=raw_data, field="complete_data")
    
    def _validate_raw_data(self, data: Dict[str, Any]) -> None:
        required_keys = {'pokemon', 'species', 'evolution_chain', 'moves'}
        missing_keys = required_keys - set(data.keys())
        
        if missing_keys:
            raise TransformationError(
                message=f"Missing required data: {missing_keys}",
                data=data,
                field="raw_data"
            )
    
    def _transform_pokemon(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self._validate_pokemon_data(data)

            stats = self._transform_stats(data.get('stats', []))
            
            transformed_data = {
                'pokedex_id': data['id'],
                'name': data['name'].lower(),
                'height': data['height'],
                'weight': data['weight'],
                'base_experience': data.get('base_experience'),
                **stats,
                
                'sprite_front_default': self._validate_url(
                    data.get('sprites', {}).get('front_default', '')
                ),
                'sprite_front_shiny': self._validate_url(
                    data.get('sprites', {}).get('front_shiny', '')
                ),
                
                # relationships
                'types': self._transform_types(data.get('types', [])),
                'abilities': self._transform_abilities(data.get('abilities', []))
            }
            
            return transformed_data
            
        except Exception as e:
            raise TransformationError(message=str(e), data=data, field="pokemon")
    
    def _validate_pokemon_data(self, data: Dict[str, Any]) -> None:
        for field, field_type in self.REQUIRED_POKEMON_FIELDS.items():
            if field not in data:
                raise TransformationError(message=f"Missing required field: {field}", data=data, field="pokemon_validation")
            
            if not isinstance(data[field], field_type):
                raise TransformationError(message=f"Invalid type for {field}. Expected {field_type.__name__}", data=data, field="pokemon_validation")
    
    def _transform_stats(self, stats_data: List[Dict[str, Any]]) -> Dict[str, int]:
        stats = {}
        for stat in stats_data:
            stat_name = stat['stat']['name']
            if stat_name in self.REQUIRED_STATS:
                stats[stat_name.replace('-', '_')] = stat['base_stat']
        
        missing_stats = set(self.REQUIRED_STATS) - {s.replace('_', '-') for s in stats.keys()}
        if missing_stats:
            logger.warning(f"Missing stats: {missing_stats}. Using default value 0.")
            for stat in missing_stats:
                stats[stat.replace('-', '_')] = 0
        
        return stats
    
    def _validate_url(self, url: str) -> str:
        if url and not url.startswith(('http://', 'https://')):
            logger.warning(f"Invalid URL format: {url}")
            return ''
        return url
    
    def _transform_types(self, types_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed_types = []
        
        for type_data in types_data:
            try:
                transformed_types.append({
                    'name': type_data['type']['name'],
                    'slot': int(type_data['slot'])
                })
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid type data: {e}")
                continue
        
        return sorted(transformed_types, key=lambda x: x['slot'])
    
    def _transform_abilities(self, abilities_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed_abilities = []
        
        for ability_data in abilities_data:
            try:
                transformed_abilities.append({
                    'name': ability_data['ability']['name'],
                    'is_hidden': bool(ability_data['is_hidden']),
                    'slot': int(ability_data['slot'])
                })
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid ability data: {e}")
                continue
        
        return sorted(transformed_abilities, key=lambda x: x['slot'])
    
    def _transform_species(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return {
                'genus': self._get_english_text(data.get('genera', []), 'genus'),
                'generation': int(data['generation']['url'].split('/')[-2]),
                'gender_rate': data['gender_rate'],
                'egg_groups': [g['name'] for g in data.get('egg_groups', [])],
                'base_happiness': data.get('base_happiness'),
                'capture_rate': data['capture_rate'],
                'is_legendary': bool(data['is_legendary']),
                'is_mythical': bool(data['is_mythical'])
            }
        except Exception as e:
            raise TransformationError(message=str(e), data=data, field="species")
    
    def _transform_evolution_chain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if 'id' not in data or 'chain' not in data:
                raise TransformationError(message="Missing required evolution chain data", data=data, field="evolution_chain")
            
            return {
                'chain_id': int(data['id']),
                'chain_data': data['chain']
            }
        except Exception as e:
            raise TransformationError(message=str(e), data=data, field="evolution_chain")
    
    def _transform_moves(self, moves_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        transformed_moves = []
        
        for move_entry in moves_data:
            try:
                move_data = move_entry['move']
                learn_details = move_entry['learn_details'][-1]  # latest
                
                transformed_moves.append({
                    'move': {
                        'name': move_data['name'],
                        'power': self._validate_stat(move_data.get('power')),
                        'pp': self._validate_stat(move_data.get('pp')),
                        'accuracy': self._validate_stat(move_data.get('accuracy')),
                        'move_type': move_data['type']['name'],
                        'damage_class': move_data['damage_class']['name'],
                        'description': self._get_english_text(
                            move_data.get('flavor_text_entries', []),
                            'flavor_text'
                        )
                    },
                    'learn_method': learn_details['move_learn_method']['name'],
                    'level_learned': self._validate_stat(
                        learn_details.get('level_learned_at')
                    ),
                    'version_group': learn_details['version_group']['name']
                })
            except (KeyError, IndexError) as e:
                logger.warning(f"Invalid move data: {e}")
                continue
        
        return transformed_moves
    
    def _get_english_text(self, entries: List[Dict[str, Any]], field: str) -> str:
        return next((e[field] for e in entries if e['language']['name'] == 'en'), '')
    
    def _validate_stat(self, value: Any) -> Optional[int]:
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None