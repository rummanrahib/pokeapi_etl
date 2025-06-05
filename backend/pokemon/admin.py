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


class PokemonAdmin(admin.ModelAdmin):
    list_display = ('name', 'pokedex_id')
    search_fields = ('name',)
    list_filter = ('types',)
    ordering = ('pokedex_id',)
    list_per_page = 100


class PokemonMoveAdmin(admin.ModelAdmin):
    list_display = ('pokemon', 'move', 'learn_method', 'level_learned')
    search_fields = ('pokemon__name', 'move__name')
    list_filter = ('learn_method',)
    ordering = ('pokemon__name', 'move__name')
    list_per_page = 100


class MoveAdmin(admin.ModelAdmin):
    list_display = ('name', 'move_type', 'damage_class')
    search_fields = ('name',)
    list_filter = ('move_type', 'damage_class')
    ordering = ('name',)
    list_per_page = 100


admin.site.register(Pokemon, PokemonAdmin)
admin.site.register(PokemonMove, PokemonMoveAdmin)
admin.site.register(Move, MoveAdmin)
admin.site.register(Type)
admin.site.register(Ability)
admin.site.register(EvolutionChain)
admin.site.register(PokemonSpecies)
