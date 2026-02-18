# Python program to find
# fibonacci number using memoization.

'''
import sqlite3
dir(sqlite3)
file = 'test.db'
conn = sqlite3.connect('test.db')
cursor = conn.cursor()
'''

import requests
import pokebase as pb
#url =  'https://pokeapi.co/api/v2/pokemon/ditto'
valid = dir(pb)
#response = requests.get(url)
#gen3 = pb.generation(3)
#moves = gen3.moves
#kanto_mon = [i.pokemon_species.name for i in pb.pokedex('kanto').pokemon_entries]

'''
def past_abilities(pastAb):
    for i in 
'''

def pokemon_get(string):
    print(f'getting {string}')
    pokemon = pb.pokemon(string)
    #we want
    #name
    name = string
    #species -> id
    species_id = pokemon.id_
    #abilities
    abilities = [{'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in pokemon.abilities]
    # past abilities
    past_abilities = [{'generation': pa.generation, 'abilities': [     {'ability': ab.ability, 'slot': ab.slot, 'is_hidden': ab.is_hidden} for ab in pa.abilities ]} for pa in pokemon.past_abilities] if hasattr(pokemon,'past_abilities') else None
    #forms likely not needed
    #games_in
    games_in = [ game.version for game in pokemon.game_indices]
    #locations
    locations = [{'location': {'location_name': loc.location_area.name, 'location_id': loc.location_area.id_}, 'version_details': [ {'encounter_details': ver.encounter_details ,'version_name':ver.version.name, 'version_id': ver.version.id_ } for ver in loc.version_details]  } for loc in pokemon.location_area_encounters]
    #stats
    stats = [ {'stat': stt.stat, 'base_stat': stt.base_stat} for stt in pokemon.stats]
    #past stats
    past_stats = [ {'generation': pst.generation, 'stats': pst.stats} for pst in pokemon.past_stats] if hasattr(pokemon, 'past_stats') else None
    #types
    types = {'1': pokemon.types[0].type, '2': pokemon.types[1].type}

    #pb.pokemon_species
    species_id = pokemon.id_
    species_name = pokemon.name
    #capture rate
    #evolution chain
    #evolves from
    #pokedexs in

    return {'name':string.upper(), 'species_id': species_id, 'abilities': abilities, 'past_abilities': past_abilities, 'types' : types, 'stats': stats, 'past_stats': past_stats, 'locations': locations}


kanto_mon = ['bulbasaur', 'ivysaur', 'venusaur', 'charmander', 'charmeleon', 'charizard', 'squirtle', 'wartortle', 'blastoise', 'caterpie', 'metapod', 'butterfree', 'weedle', 'kakuna', 'beedrill',
             'pidgey', 'pidgeotto', 'pidgeot', 'rattata', 'raticate', 'spearow', 'fearow', 'ekans', 'arbok', 'pikachu', 'raichu', 'sandshrew', 'sandslash', 'nidoran-f', 'nidorina', 'nidoqueen',
             'nidoran-m', 'nidorino', 'nidoking', 'clefairy', 'clefable', 'vulpix', 'ninetales', 'jigglypuff', 'wigglytuff', 'zubat', 'golbat', 'oddish', 'gloom', 'vileplume', 'paras', 'parasect',
             'venonat', 'venomoth', 'diglett', 'dugtrio', 'meowth', 'persian', 'psyduck', 'golduck', 'mankey', 'primeape', 'growlithe', 'arcanine', 'poliwag', 'poliwhirl', 'poliwrath', 'abra',
             'kadabra', 'alakazam', 'machop', 'machoke', 'machamp', 'bellsprout', 'weepinbell', 'victreebel', 'tentacool', 'tentacruel', 'geodude', 'graveler', 'golem', 'ponyta', 'rapidash',
             'slowpoke', 'slowbro', 'magnemite', 'magneton', 'farfetchd', 'doduo', 'dodrio', 'seel', 'dewgong', 'grimer', 'muk', 'shellder', 'cloyster', 'gastly', 'haunter', 'gengar', 'onix',
             'drowzee', 'hypno', 'krabby', 'kingler', 'voltorb', 'electrode', 'exeggcute', 'exeggutor', 'cubone', 'marowak', 'hitmonlee', 'hitmonchan', 'lickitung', 'koffing', 'weezing', 'rhyhorn',
             'rhydon', 'chansey', 'tangela', 'kangaskhan', 'horsea', 'seadra', 'goldeen', 'seaking', 'staryu', 'starmie', 'mr-mime', 'scyther', 'jynx', 'electabuzz', 'magmar', 'pinsir', 'tauros',
             'magikarp', 'gyarados', 'lapras', 'ditto', 'eevee', 'vaporeon', 'jolteon', 'flareon', 'porygon', 'omanyte', 'omastar', 'kabuto', 'kabutops', 'aerodactyl', 'snorlax', 'articuno',
             'zapdos', 'moltres', 'dratini', 'dragonair', 'dragonite', 'mewtwo', 'mew']
#pokemon_get('bulbasaur')
print('beginning loop')
lst = [pokemon_get(kanto_mon[i]) for i in range(3)]

for i in range(3):
    #if not in table
    pokemon = pokemon_get(kanto_mon[i])





print('done')



#[i.pokemon_species for i in pb.pokedex('kanto').pokemon_entries]

#kanto_mon = [i.pokemon_species.name for i in pb.pokedex('kanto').pokemon_entries]