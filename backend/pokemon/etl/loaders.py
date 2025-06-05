import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Q

from ..models import (
    Ability,
    EvolutionChain,
    Move,
    Pokemon,
    PokemonMove,
    PokemonSpecies,
    Type,
)

logger = logging.getLogger(__name__)

@dataclass
class LoaderError(Exception):
    message: str
    model: str
    data: Optional[Dict[str, Any]] = None

class PokemonDataLoader:    
    def __init__(self):
        # caching to minimize db queries
        self._type_cache = {}
        self._ability_cache = {}
        self._move_cache = {}
        self._evolution_chain_cache = {}
        self._stats_initialized = False
    
    @transaction.atomic
    def load_complete_pokemon_data(self, data: Dict[str, Any]) -> Tuple[Pokemon, PokemonSpecies]:
        try:
            self._validate_complete_data(data)
            
            # load in correct order to maintain relationships
            evolution_chain = self._load_evolution_chain(data['evolution_chain'])
            pokemon = self._load_pokemon(data['pokemon'], evolution_chain)
            species = self._load_species(data['species'], pokemon)
            self._load_moves(data['moves'], pokemon)
            
            logger.info(f"Successfully loaded Pokemon: {pokemon.name} (#{pokemon.pokedex_id})")
            return pokemon, species
            
        except LoaderError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in complete Pokemon load: {e}")
            raise LoaderError(message=f"Failed to load Pokemon data: {str(e)}", model="complete_load", data=data)
    
    def _validate_complete_data(self, data: Dict[str, Any]) -> None:
        required_keys = {'pokemon', 'species', 'evolution_chain', 'moves'}
        missing_keys = required_keys - set(data.keys())
        
        if missing_keys:
            raise LoaderError(message=f"Missing required data sections: {missing_keys}", model="validation", data=data)
    
    def _load_pokemon(self, data: Dict[str, Any], evolution_chain: EvolutionChain) -> Pokemon:
        try:
            # validate required fields
            required_fields = {
                'pokedex_id', 'name', 'height', 'weight',
                'hp', 'attack', 'defense', 'special_attack',
                'special_defense', 'speed'
            }
            missing_fields = required_fields - set(data.keys())
            if missing_fields:
                raise LoaderError(message=f"Missing required Pokemon fields: {missing_fields}", model="Pokemon", data=data)
            
            # extract relationship data
            types_data = data.pop('types', [])
            abilities_data = data.pop('abilities', [])
            
            # create or update Pokemon
            pokemon, created = Pokemon.objects.update_or_create(
                pokedex_id=data['pokedex_id'],
                defaults={
                    **data,
                    'evolution_chain': evolution_chain
                }
            )
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} Pokemon: {pokemon.name} (#{pokemon.pokedex_id})")
            
            # handle relationships
            self._handle_types(pokemon, types_data)
            self._handle_abilities(pokemon, abilities_data)
            
            return pokemon
            
        except DatabaseError as e:
            logger.error(f"Database error loading Pokemon {data.get('name')}: {e}")
            raise LoaderError(message=f"Database error: {str(e)}", model="Pokemon", data=data)
        except Exception as e:
            logger.error(f"Error loading Pokemon {data.get('name')}: {e}")
            raise LoaderError(message=str(e), model="Pokemon", data=data)
    
    def _load_evolution_chain(self, data: Dict[str, Any]) -> EvolutionChain:
        try:
            chain_id = data['chain_id']
            
            if chain_id not in self._evolution_chain_cache:
                chain, _ = EvolutionChain.objects.update_or_create(
                    chain_id=chain_id,
                    defaults={'chain_data': data['chain_data']}
                )
                self._evolution_chain_cache[chain_id] = chain
                logger.debug(f"Cached evolution chain #{chain_id}")
            
            return self._evolution_chain_cache[chain_id]
            
        except Exception as e:
            raise LoaderError(message=f"Failed to load evolution chain: {str(e)}", model="EvolutionChain", data=data)
    
    def _load_species(self, data: Dict[str, Any], pokemon: Pokemon) -> PokemonSpecies:
        try:
            required_fields = {
                'gender_rate', 'capture_rate', 'is_legendary',
                'is_mythical', 'egg_groups'
            }
            missing_fields = required_fields - set(data.keys())
            if missing_fields:
                raise LoaderError(message=f"Missing required species fields: {missing_fields}", model="PokemonSpecies", data=data)
            
            species, created = PokemonSpecies.objects.update_or_create(pokemon=pokemon, defaults=data)
            
            action = "Created" if created else "Updated"
            logger.info(f"{action} species data for {pokemon.name}")
            
            return species
            
        except Exception as e:
            raise LoaderError(message=f"Failed to load species data: {str(e)}", model="PokemonSpecies", data=data)
    
    def _handle_types(self, pokemon: Pokemon, types_data: List[Dict[str, Any]]) -> None:
        try:
            type_objects = []
            
            for type_data in types_data:
                if 'name' not in type_data:
                    logger.warning(f"Invalid type data for {pokemon.name}: {type_data}")
                    continue
                
                type_name = type_data['name']
                if type_name not in self._type_cache:
                    type_obj, _ = Type.objects.get_or_create(name=type_name)
                    self._type_cache[type_name] = type_obj
                    logger.debug(f"Cached type: {type_name}")
                
                type_objects.append(self._type_cache[type_name])
            
            pokemon.types.set(type_objects)
            logger.info(f"Set types for {pokemon.name}: {[t.name for t in type_objects]}")
            
        except Exception as e:
            raise LoaderError(
                message=f"Failed to handle types: {str(e)}",
                model="Type",
                data={'pokemon': pokemon.name, 'types': types_data}
            )
    
    def _handle_abilities(self, pokemon: Pokemon, abilities_data: List[Dict[str, Any]]) -> None:
        try:
            ability_objects = []
            
            for ability_data in abilities_data:
                if 'name' not in ability_data:
                    logger.warning(f"Invalid ability data for {pokemon.name}: {ability_data}")
                    continue
                
                ability_name = ability_data['name']
                if ability_name not in self._ability_cache:
                    ability_obj, _ = Ability.objects.get_or_create(
                        name=ability_name,
                        defaults={
                            'effect': '',
                            'short_effect': ''
                        }
                    )
                    self._ability_cache[ability_name] = ability_obj
                    logger.debug(f"Cached ability: {ability_name}")
                
                ability_objects.append(self._ability_cache[ability_name])
            
            pokemon.abilities.set(ability_objects)
            logger.info(f"Set abilities for {pokemon.name}: {[a.name for a in ability_objects]}")
            
        except Exception as e:
            raise LoaderError(
                message=f"Failed to handle abilities: {str(e)}",
                model="Ability",
                data={'pokemon': pokemon.name, 'abilities': abilities_data}
            )
    
    def _load_moves(self, moves_data: List[Dict[str, Any]], pokemon: Pokemon) -> None:
        try:
            for move_entry in moves_data:
                self._validate_move_data(move_entry)
                move_data = move_entry['move']
                move_type = self._get_or_create_type(move_data['move_type'])
                move = self._get_or_create_move(move_data, move_type)
                
                # relationship
                self._create_pokemon_move(pokemon, move, move_entry)
            
            logger.info(f"Loaded {len(moves_data)} moves for {pokemon.name}")
            
        except Exception as e:
            raise LoaderError(
                message=f"Failed to load moves: {str(e)}", model="Move",
                data={'pokemon': pokemon.name, 'moves': moves_data}
            )
    
    def _validate_move_data(self, move_entry: Dict[str, Any]) -> None:
        required_fields = {
            'move': {'name', 'move_type', 'damage_class'},
            'learn_method': None,
        }
        
        for field, subfields in required_fields.items():
            if field not in move_entry:
                raise LoaderError(message=f"Missing required field: {field}", model="Move", data=move_entry)
            if subfields and not all(sf in move_entry['move'] for sf in subfields):
                raise LoaderError(message=f"Missing required move subfields: {subfields}", model="Move", data=move_entry['move'])
    
    def _get_or_create_type(self, type_name: str) -> Type:
        if type_name not in self._type_cache:
            type_obj, _ = Type.objects.get_or_create(name=type_name)
            self._type_cache[type_name] = type_obj
            logger.debug(f"Cached type: {type_name}")
        return self._type_cache[type_name]
    
    def _get_or_create_move(self, move_data: Dict[str, Any], move_type: Type) -> Move:
        move_name = move_data['name']
        if move_name not in self._move_cache:
            move, _ = Move.objects.update_or_create(
                name=move_name,
                defaults={
                    **move_data,
                    'move_type': move_type
                }
            )
            self._move_cache[move_name] = move
            logger.debug(f"Cached move: {move_name}")
        return self._move_cache[move_name]
    
    def _create_pokemon_move(self, pokemon: Pokemon, move: Move, move_entry: Dict[str, Any]) -> None:
        PokemonMove.objects.update_or_create(
            pokemon=pokemon,
            move=move,
            learn_method=move_entry['learn_method'],
            defaults={
                'level_learned': move_entry.get('level_learned')
            }
        )
    
    def clear_caches(self) -> None:
        self._type_cache.clear()
        self._ability_cache.clear()
        self._move_cache.clear()
        self._evolution_chain_cache.clear()
        logger.debug("Cleared all caches")