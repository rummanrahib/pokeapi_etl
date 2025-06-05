from typing import List

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import QuerySet


class Type(models.Model):
    name: str = models.CharField(max_length=50, unique=True, db_index=True)
    
    def __str__(self) -> str:
        return self.name


class Ability(models.Model):
    name: str = models.CharField(max_length=100, unique=True, db_index=True)
    effect: str = models.TextField(blank=True)
    short_effect: str = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Abilities'
    
    def __str__(self) -> str:
        return self.name


class EvolutionChain(models.Model):
    chain_id: int = models.IntegerField(unique=True, db_index=True)
    chain_data: dict = models.JSONField()
    
    class Meta:
        ordering = ['chain_id']
        verbose_name_plural = 'Evolution Chains'
    
    def __str__(self) -> str:
        return f'Evolution Chain #{self.chain_id}'


# Pokémon with its base attributes and stats
class Pokemon(models.Model):
    pokedex_id: int = models.IntegerField(unique=True, db_index=True)
    name: str = models.CharField(max_length=100, db_index=True)
    height: int = models.IntegerField(help_text='Height in decimeters')
    weight: int = models.IntegerField(help_text='Weight in hectograms')
    base_experience: int | None = models.IntegerField(null=True, blank=True)
    
    # Base Stats
    hp: int = models.PositiveIntegerField()
    attack: int = models.PositiveIntegerField()
    defense: int = models.PositiveIntegerField()
    special_attack: int = models.PositiveIntegerField()
    special_defense: int = models.PositiveIntegerField()
    speed: int = models.PositiveIntegerField()
    
    # Relationships
    types: QuerySet[Type] = models.ManyToManyField(Type)
    abilities: QuerySet[Ability] = models.ManyToManyField(Ability)
    evolution_chain: EvolutionChain | None = models.ForeignKey(
        EvolutionChain,
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='pokemon'
    )
    
    # Sprite URLs
    sprite_front_default: str = models.URLField(blank=True)
    sprite_front_shiny: str = models.URLField(blank=True)
    
    class Meta:
        ordering = ['pokedex_id']
    
    def __str__(self) -> str:
        return f'#{self.pokedex_id}. {self.name.title()}'
    
    @property
    def total_stats(self) -> int:
        return sum([
            self.hp,
            self.attack,
            self.defense,
            self.special_attack,
            self.special_defense,
            self.speed
        ])


# Extended species information for a Pokémon
class PokemonSpecies(models.Model):
    pokemon: Pokemon = models.OneToOneField(Pokemon, on_delete=models.CASCADE, related_name='species')
    genus: str = models.CharField(max_length=100, blank=True)
    generation: int = models.PositiveIntegerField()
    gender_rate: int = models.IntegerField(help_text='-1 for genderless, or 0-8 for female ratio')
    egg_groups: List[str] = ArrayField(models.CharField(max_length=50), default=list)
    base_happiness: int | None = models.PositiveIntegerField(null=True, blank=True)
    capture_rate: int = models.PositiveIntegerField()
    is_legendary: bool = models.BooleanField(default=False)
    is_mythical: bool = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['pokemon__pokedex_id']
        verbose_name_plural = 'Pokemon Species'
    
    def __str__(self) -> str:
        return f'{self.pokemon.name} Species'


# Represents a move/attack that can be learned by Pokémon
class Move(models.Model):
    class DamageClass(models.TextChoices):
        PHYSICAL = 'physical', 'Physical'
        SPECIAL = 'special', 'Special'
        STATUS = 'status', 'Status'

    name: str = models.CharField(max_length=100, unique=True, db_index=True)
    power: int | None = models.PositiveIntegerField(null=True, blank=True)
    pp: int | None = models.PositiveIntegerField(null=True, blank=True)
    accuracy: int | None = models.PositiveIntegerField(null=True, blank=True)
    move_type: Type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name='moves')
    damage_class: str = models.CharField(max_length=20, choices=DamageClass.choices)
    description: str = models.TextField(blank=True)
    
    def __str__(self) -> str:
        return self.name


# Represents how a Pokémon learns a specific move
class PokemonMove(models.Model):
    class LearnMethod(models.TextChoices):
        LEVEL_UP = 'level-up', 'Level Up'
        MACHINE = 'machine', 'TM/TR'
        EGG = 'egg', 'Egg Move'
        TUTOR = 'tutor', 'Move Tutor'
    
    pokemon: Pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name='moves')
    move: Move = models.ForeignKey(Move, on_delete=models.CASCADE)
    learn_method: str = models.CharField(max_length=20, choices=LearnMethod.choices)
    level_learned: int | None = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text='Required only for level-up moves'
    )
    
    class Meta:
        unique_together = ['pokemon', 'move', 'learn_method']
        verbose_name_plural = 'Pokemon Moves'   
    
    def __str__(self) -> str:
        return f'{self.pokemon.name} | {self.move.name} | {self.learn_method}'