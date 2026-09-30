# Blaze Black early item seed analysis

Analysis completed and implemented locally 2026-09-23 through
`Backend/migrations/20260923_blazeblack_split_item_sources.sql`. Production
remains untouched.

## Scope and sources

- Game: Blaze Black 3.1, `game_id=1001`, through Burgh (`badge:35`).
- Encounter availability comes from the local Blaze Black encounter tables.
- Wild held items and base held rates come from Serebii's Black/White held-item
  table supplied by the user. Blaze Black rewrites encounters but the available
  evidence and community routing use the Black/White species held-item data.
- Dust-cloud contents and category rates come from Bulbapedia's Generation V
  phenomenon table.
- TM46 Thief is on Wellspring Cave 1F and is available before Lenora.

Progression corrections are required before joining encounter rows to items:

- Pinwheel Forest **Outside** is accessible before Lenora even though the
  current attempt script places the combined Pinwheel location after Lenora.
- Pinwheel Forest **Inside** opens after Lenora and belongs to Burgh's segment.
- Route 1 dark grass is Surf-gated and is not an early source.
- Surf and surf-spot encounters are unavailable. Blaze Black moves the Super
  Rod to Route 3, so ordinary and rippling fishing encounters are available.
- Wellspring Cave B1F remains Surf-gated; only 1F is counted.

## Lenora: wild held-item candidates

There are 44 unique item names on accessible species. Percentages below are
the species' base held-item rates, not encounter rates. The display names
`Silver Powder` and `Twisted Spoon` should use spaces even though Serebii's
page concatenates them.

| Item | Held rate | Available source examples |
| --- | ---: | --- |
| Big Pearl | 5% | Shellder, Wellspring Cave 1F fishing |
| Black Belt | 5% | Throh or Sawk, Pinwheel Outside dark grass |
| Black Sludge | 5% | Croagunk, Pinwheel Outside grass |
| Charti Berry | 5% | Taillow, Route 3 grass |
| Cheri Berry | 50% | Blitzle, Route 3 dark grass |
| Chesto Berry | 5% | Spinda, Whismur |
| Chilan Berry | 5% | Rattata, Route 1 grass |
| Coba Berry | 5% | Sunkern, Route 3 grass |
| Colbur Berry | 5% | Chingling, Dreamyard shaking grass; see exception below |
| Comet Shard | 1% | Clefairy, Cleffa, Lunatone, or Solrock |
| Deep Sea Scale | 5% | Chinchou, Route 3 fishing |
| Deep Sea Tooth | 5% | Basculin, Route 1 or Striaton rippling fishing |
| Dragon Scale | 5% | Dratini, Route 1 rippling fishing |
| Everstone | 5% / 50% | Geodude 5%; Roggenrola 50%, Wellspring 1F |
| Expert Belt | 1% | Throh or Sawk, Pinwheel Outside dark grass |
| Haban Berry | 5% | Gible, Wellspring 1F dust-cloud encounter |
| Hard Stone | 5% | Roggenrola or Aron, Wellspring 1F |
| Lagging Tail | 5% | Slowpoke, Striaton or Route 3 fishing |
| Leppa Berry | 5% / 50% | Skitty 5%; Clefairy or Cleffa 50% |
| Lucky Egg | 5% | Happiny, Route 1 shaking grass |
| Metal Coat | 5% | Bronzor, Wellspring 1F |
| Metronome | 5% | Kricketot, Route 2 grass |
| Moon Stone | 5% | Clefairy, Cleffa, or Lunatone |
| Oran Berry | 5% / 50% | Sentret or Zigzagoon 5%; Audino 50% |
| Oval Stone | 50% | Happiny, Route 1 shaking grass |
| Passho Berry | 5% | Phanpy, Route 3 grass |
| Payapa Berry | 5% | Mankey, Route 2 grass |
| Pearl | 50% | Shellder, Wellspring 1F fishing |
| Pecha Berry | 5% | Poochyena, Route 2 grass |
| Persim Berry | 50% | Tympole, Pinwheel Outside grass |
| Poison Barb | 5% | Beedrill, Budew, Qwilfish, or Tentacool |
| Quick Claw | 5% | Meowth, Route 2 grass |
| Rawst Berry | 100% | Growlithe or Vulpix, Route 3 dark grass |
| Sharp Beak | 5% | Doduo, Pinwheel Outside dark grass |
| Shed Shell | 5% | Beautifly, Dustox, or Venomoth |
| Silver Powder | 5% | Butterfree, Route 2 shaking grass |
| Sitrus Berry | 5% | Audino on several early shaking-grass tables |
| Soft Sand | 5% | Diglett, Wellspring 1F dust-cloud encounter |
| Star Piece | 5% / 100% | Staryu 5%; Jirachi 100% |
| Stardust | 50% | Staryu, Striaton fishing |
| Sun Stone | 5% | Solrock, Dreamyard shaking grass |
| Thick Club | 5% | Cubone, Pinwheel Outside dark grass |
| Twisted Spoon | 5% | Abra, Route 3 grass |
| Yache Berry | 5% | Starly, Route 1 grass |

### Colbur Berry exception

Thief is a Dark attack. A Chingling hit super-effectively consumes its Colbur
Berry before Thief can take it, so `Thief - Chingling 5%` would be misleading.
Keep Colbur out of the ordinary Thief seed or record it as a separate conditional
method such as Pickup/Covet after the berry is consumed. This needs an explicit
product choice before seeding.

## Lenora: dust-cloud system

Dust clouds are available on Wellspring Cave 1F after the first badge. A cloud
is 40% Pokémon and 60% item. Conditional on getting an item, the category rates
are 85% gem, 10% evolution stone, and 5% Everstone. The item pool's weights make
each gem and Everstone 3% of all clouds, and each listed stone 0.6% of all
clouds.

| Group | Per-item cloud rate | Items |
| --- | ---: | --- |
| Gems | 3% | Fire, Water, Electric, Grass, Ice, Fighting, Poison, Ground, Flying, Psychic, Bug, Rock, Ghost, Dragon, Dark, Steel, Normal Gem |
| Stones | 0.6% | Sun, Moon, Fire, Water, Thunder, Leaf, Shiny, Dusk, Dawn, Oval Stone |
| Other | 3% | Everstone |

The 28 dust-cloud names overlap four held-item names available at Lenora:
Everstone, Moon Stone, Oval Stone, and Sun Stone. After excluding Colbur from
ordinary Thief, Lenora has 67 unique item names across Thief and dust clouds.

## Burgh: newly accessible Pinwheel Inside sources

These ten item names come from species in Pinwheel Forest Inside. Five names
are already available before Lenora; the genuinely new names are Kebia Berry,
King's Rock, Mental Herb, Occa Berry, and Rindo Berry.

| Item | Held rate | Sources |
| --- | ---: | --- |
| Kebia Berry | 5% | Shroomish |
| King's Rock | 5% | Poliwhirl or Politoed, rippling fishing |
| Mental Herb | 5% | Sewaddle or Swadloon |
| Occa Berry | 5% | Pansage |
| Oran Berry | 50% | Audino, Pansage, Pansear, or Panpour |
| Passho Berry | 5% | Pansear |
| Pecha Berry | 50% | Venipede or Whirlipede |
| Poison Barb | 5% | Venipede, Whirlipede, or Roselia |
| Rindo Berry | 5% | Panpour |
| Sitrus Berry | 5% | Audino |

## Design and schema recommendation

The current `curated_split_items(item_name, method)` model would create one
very long Lenora card and either duplicate item names or flatten several
sources into hard-to-edit text. Preserve it as the parent item record and add
structured acquisition rows before seeding:

```text
curated_split_item_sources
  item_source_id
  item_record_id -> curated_split_items
  method_kind       thief | dust_cloud | manual
  species_id        nullable
  chance_percent    nullable
  source_detail     nullable free text
  source_url        nullable provenance
  sort_order
```

Store an item once at the earliest split where it is available. Multiple
species and methods become child sources. Do not copy Lenora's full library
onto Burgh; Burgh adds its newly available sources while the timeline preserves
the earlier source-of-truth entry.

For the 330px panel, group items under collapsible `Thief` and `Dust clouds`
sections with counts. Show one compact row per unique item and its best/base
rate; expanding a row reveals all species sources. Dust clouds should render as
three compact subgroups (Gems, Stones, Other), avoiding 28 full table rows.
The existing All / Parties / Items filter can remain unchanged.

Admin entry can retain the simple split/item/method path for manual additions,
with structured source fields exposed only when the method is Thief or dust
cloud. Seed `game_id=1001` only; Volt White should be verified separately.

## Implementation gate

Before implementation, decide how to represent Colbur Berry. Everything else
in this document is ready to become a reviewed seed migration after the
additive source-table/UI change.
