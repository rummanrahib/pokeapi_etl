from django.contrib import admin

from .models import (
    Ability,
    EvolutionChain,
    Move,
    Pokemon,
    PokemonMove,
    PokemonSpecies,
    Type,
)

admin.site.register(Type)
admin.site.register(Ability)
admin.site.register(EvolutionChain)
admin.site.register(Move)
admin.site.register(Pokemon)
admin.site.register(PokemonMove)
admin.site.register(PokemonSpecies)
