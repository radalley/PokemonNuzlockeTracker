# Lockley - Multi Game Pokemon Nuzlocke Tracker

Lockley is a Pokémon campaign Nuzlocke tracker designed to track runs and attempts across all generations of the core series games. Users can accurately track their encounters and trainer progress.

**Link to application:** https://pokemon-nuzlocke-tracker-beta.vercel.app/

<img width="843" height="527" alt="image" src="https://github.com/user-attachments/assets/ce17f0c1-b63d-4722-8c10-fb80abb98ed7" />

## What is a Nuzlocke? ##

A Nuzlocke is a community-made challenge meant to increase the difficulty of the games while maintaining an authentic adventure experience.

Core Rules:
1) The player may only catch the first wild Pokémon encountered in each area, and no others. If the first wild Pokémon encountered faints or flees, there are no second chances.
2) Any Pokémon that faints is considered dead and must be released. Revival methods such as Revive, Revival Blessing, etc., are forbidden. If the player runs out of living Pokémon, they've failed the challenge and must restart the game.

## How It's Made:

**Frontend Tech:** JavaScript, React, Vite deployed via Vercel.

**Backend Tech:** Python, Flask, FastAPI deployed via Render.

**Database:** Postgres via Supabase.

**Data seeding and acquisition:** PokeBase used in the backend via PokeAPI for locations, encounters, and Pokémon stats. Trainer data acquired via decompilations of GBA ROMs.

**Sign-in and Authentication:** Handled through Supabase with Google OAuth

## Optimizations
**Caching:** This system uses caching for static data, such as sprites, trainer data, and encounter pools.

**Patching:** Used to apply changes from cross-generation balancing, such as new types, moves, and stats.

**Local Data:** Lockley can be used without an account, with data saved into local storage.

**Frontend components:** Components were used to normalize data objects across pages and tables. Notable examples are Pokémon and Trainer display cards.

**Locations:** An alias table is used to tie encounter pools together under the same parent. Now, locations like Mt. Moon Floor A, Mt. Moon Floor B, and Mt. Moon Roof can all be held under the same identifier, Mt. Moon.

## Lessons Learned

**The data:** Pokémon by nature is a fleet of data. Pokebase was an incredible tool to acquire and seed data by generation. 

One limitation on Pokebase is that trainer data is not compiled anywhere online or in the API. There exist the GBA games decomplied online in their original C code. That was scraped and used to seed trainer pools, but research is being done to acquire generations 4+.

Pokémon regularly balances species data over the years. Originally, I had one table for species stats, but I have since split each stat section into its own table, with a version_group identifier to track changes over the years. Tables became abilities, types, and stats, allowing joins to bring in data accurately reflecting the latest patch.

Trainers change based on the starter selected. This program allows users to specify their starter and have Trainers adjust.

**Sprites:** Pokémon PNGs were fun because, for this project's design, I wanted the Pokémon themselves to reflect my favorite style from the Generation 5 sprites. As Pokémon leaped into 3D in 2013, sprites were no longer the standard for future games. Community artists were so creative that they created sprites for the new Pokémon as they were released. As such, we have PNGs for all 1025+ Pokémon! I did debate using the animated sprites for Pokémon from Gen 1-5, but decided not to keep the style consistent. 

## Planned Features 
- Trainer Pools across all games
- Add Location items to grab
- Functionality to view Pokémon Movesets
- Rebuilt UI to match selected game visuals
- Career Stats Page to view Pokémon across all runs
- Revamp the death screen, adding logs
- Genlocke functionally, allowing carryover to the next run

## Screenshots:
**Attempt page:**
<img width="405" height="230" alt="image" src="https://github.com/user-attachments/assets/d7c16dba-8d6a-4440-a727-73eb116dba42" />
**Encounter View:**
<img width="414" height="205" alt="image" src="https://github.com/user-attachments/assets/65556c69-8575-49fa-9d2f-97971bd3e1ac" /> 
**Trainer View:**
<img width="409" height="308" alt="image" src="https://github.com/user-attachments/assets/05f22655-da40-4dc5-86f4-4ff7026cd1bd" />
**Box View:**
<img width="354" height="409" alt="image" src="https://github.com/user-attachments/assets/8104f5e3-6ee9-4cbe-abe4-a5c2810df0a4" />

## Sources and Tools used ##
**PokeAPI:** https://pokeapi.co/

**Serebii:** https://www.serebii.net/

**Bulbapedia:** https://bulbapedia.bulbagarden.net/

**PokemonDB:** https://pokemondb.net/

**Game Decompilations:** https://github.com/pret
