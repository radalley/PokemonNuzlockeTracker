// Maps trainer_class + optional trainer_name to a sprite filename stem.
// Full path: /sprites/trainers/gen3/Spr_FRLG_<stem>.png

// Named trainers — checked first when trainer_name is provided
const NAME_MAP = {
  'AGATHA':    'Agatha',
  'BLAINE':    'Blaine',
  'BLUE':      'Blue_1',
  'GARY':      'Blue_1',
  'BROCK':     'Brock',
  'BRUNO':     'Bruno',
  'DAISY':     'Daisy_Oak',
  'ERIKA':     'Erika',
  'GIOVANNI':  'Giovanni',
  'KOGA':      'Koga',
  'LANCE':     'Lance',
  'LORELEI':   'Lorelei',
  'LT.SURGE': 'Lt_Surge',
  'MISTY':     'Misty',
  'SABRINA':   'Sabrina',
}
// Class-level fallbacks
const CLASS_MAP = {
  TRAINER_CLASS_YOUNGSTER:        'Youngster',
  TRAINER_CLASS_BUG_CATCHER:      'Bug_Catcher',
  TRAINER_CLASS_LASS:              'Lass',
  TRAINER_CLASS_SAILOR:            'Sailor',
  TRAINER_CLASS_CAMPER:            'Camper',
  TRAINER_CLASS_PICNICKER:         'Picnicker',
  TRAINER_CLASS_POKEMANIAC:        'PokéManiac',
  TRAINER_CLASS_SUPER_NERD:        'Super_Nerd',
  TRAINER_CLASS_HIKER:             'Hiker',
  TRAINER_CLASS_BIKER:             'Biker',
  TRAINER_CLASS_BURGLAR:           'Burglar',
  TRAINER_CLASS_ENGINEER:          'Engineer',
  TRAINER_CLASS_FISHERMAN:         'Fisherman',
  TRAINER_CLASS_SWIMMER_M:         'Swimmer_M',
  TRAINER_CLASS_SWIMMER_F:         'Swimmer_F',
  TRAINER_CLASS_CUE_BALL:          'Cue_Ball',
  TRAINER_CLASS_GAMER:             'Gamer',
  TRAINER_CLASS_BEAUTY:            'Beauty',
  TRAINER_CLASS_PSYCHIC:           'Psychic_M',
  TRAINER_CLASS_ROCKER:            'Rocker',
  TRAINER_CLASS_JUGGLER:           'Juggler',
  TRAINER_CLASS_TAMER:             'Tamer',
  TRAINER_CLASS_BIRD_KEEPER:       'Bird_Keeper',
  TRAINER_CLASS_BLACK_BELT:        'Black_Belt',
  TRAINER_CLASS_RIVAL:             'Blue_1',
  TRAINER_CLASS_SCIENTIST:         'Scientist',
  TRAINER_CLASS_BOSS:              'Giovanni',
  TRAINER_CLASS_TEAM_ROCKET:       'Team_Rocket_Grunt_M',
  TRAINER_CLASS_COOLTRAINER:       'Cooltrainer_M',
  TRAINER_CLASS_ELITE_FOUR:        null,   // resolved by trainer_name above
  TRAINER_CLASS_LEADER:            null,   // resolved by trainer_name above
  TRAINER_CLASS_CHAMPION:          'Blue_1',
  TRAINER_CLASS_GENTLEMAN:         'Gentleman',
  TRAINER_CLASS_CHANNELER:         'Channeler',
  TRAINER_CLASS_TWINS:             'Twins',
  TRAINER_CLASS_COOL_COUPLE:       'Cool_Couple',
  TRAINER_CLASS_YOUNG_COUPLE:      'Young_Couple',
  TRAINER_CLASS_CRUSH_KIN:         'Crush_Kin',
  TRAINER_CLASS_SIS_AND_BRO:       'Sis_and_Bro',
  TRAINER_CLASS_CRUSH_GIRL:        'Crush_Girl',
  TRAINER_CLASS_TUBER:             'Tuber',
  TRAINER_CLASS_PKMN_BREEDER:      'Pokémon_Breeder',
  TRAINER_CLASS_PKMN_RANGER:       'Pokémon_Ranger_M',
  TRAINER_CLASS_AROMA_LADY:        'Aroma_Lady',
  TRAINER_CLASS_RUIN_MANIAC:       'Ruin_Maniac',
  TRAINER_CLASS_LADY:              'Lady',
  // RS equivalents mapped to FRLG sprites
  TRAINER_CLASS_RS_YOUNGSTER:      'Youngster',
  TRAINER_CLASS_RS_BUG_CATCHER:    'Bug_Catcher',
  TRAINER_CLASS_RS_LASS:           'Lass',
  TRAINER_CLASS_RS_SAILOR:         'Sailor',
  TRAINER_CLASS_RS_CAMPER:         'Camper',
  TRAINER_CLASS_RS_PICNICKER:      'Picnicker',
  TRAINER_CLASS_RS_POKEMANIAC:     'PokéManiac',
  TRAINER_CLASS_RS_HIKER:          'Hiker',
  TRAINER_CLASS_RS_FISHERMAN:      'Fisherman',
  TRAINER_CLASS_RS_SWIMMER_M:      'Swimmer_M',
  TRAINER_CLASS_RS_SWIMMER_F:      'Swimmer_F',
  TRAINER_CLASS_RS_BEAUTY:         'Beauty',
  TRAINER_CLASS_RS_PSYCHIC:        'Psychic_M',
  TRAINER_CLASS_RS_GENTLEMAN:      'Gentleman',
  TRAINER_CLASS_RS_BIRD_KEEPER:    'Bird_Keeper',
  TRAINER_CLASS_RS_BLACK_BELT:     'Black_Belt',
  TRAINER_CLASS_RS_COOLTRAINER:    'Cooltrainer_M',
  TRAINER_CLASS_RS_ELITE_FOUR:     null,
  TRAINER_CLASS_RS_LEADER:         null,
  TRAINER_CLASS_RS_CHAMPION:       null,
  TRAINER_CLASS_RS_TWINS:          'Twins',
  TRAINER_CLASS_RS_SIS_AND_BRO:    'Sis_and_Bro',
  TRAINER_CLASS_RS_YOUNG_COUPLE:   'Young_Couple',
  TRAINER_CLASS_RS_TUBER_F:        'Tuber',
  TRAINER_CLASS_RS_TUBER_M:        'Tuber',
  TRAINER_CLASS_RS_PKMN_BREEDER:   'Pokémon_Breeder',
  TRAINER_CLASS_RS_PKMN_RANGER:    'Pokémon_Ranger_M',
  TRAINER_CLASS_RS_AROMA_LADY:     'Aroma_Lady',
  TRAINER_CLASS_RS_RUIN_MANIAC:    'Ruin_Maniac',
  TRAINER_CLASS_RS_LADY:           'Lady',
  // No sprite available for these classes
  TRAINER_CLASS_INTERVIEWER:       null,
  TRAINER_CLASS_HEX_MANIAC:        null,
  TRAINER_CLASS_RICH_BOY:          null,
  TRAINER_CLASS_GUITARIST:         null,
  TRAINER_CLASS_KINDLER:           null,
  TRAINER_CLASS_BUG_MANIAC:        null,
  TRAINER_CLASS_SCHOOL_KID:        null,
  TRAINER_CLASS_SR_AND_JR:         null,
  TRAINER_CLASS_POKEFAN:           null,
  TRAINER_CLASS_EXPERT:            null,
  TRAINER_CLASS_TRIATHLETE:        null,
  TRAINER_CLASS_DRAGON_TAMER:      null,
  TRAINER_CLASS_NINJA_BOY:         null,
  TRAINER_CLASS_BATTLE_GIRL:       null,
  TRAINER_CLASS_PARASOL_LADY:      null,
  TRAINER_CLASS_BOARDER:           null,
  TRAINER_CLASS_COLLECTOR:         null,
  TRAINER_CLASS_PKMN_TRAINER:      null,
  TRAINER_CLASS_MAGMA_LEADER:      null,
  TRAINER_CLASS_TEAM_MAGMA:        null,
  TRAINER_CLASS_OLD_COUPLE:        null,
  TRAINER_CLASS_AQUA_ADMIN:        null,
  TRAINER_CLASS_MAGMA_ADMIN:       null,
  TRAINER_CLASS_AQUA_LEADER:       null,
  TRAINER_CLASS_TEAM_AQUA:         null,
  TRAINER_CLASS_PKMN_PROF:         null,
  TRAINER_CLASS_PLAYER:            null,
  TRAINER_CLASS_PAINTER:           null,
}

/**
 * Returns the full src path for a trainer sprite, or null if none available.
 * @param {string} trainerClass - e.g. 'TRAINER_CLASS_LEADER'
 * @param {string} trainerName  - e.g. 'Brock'
 */
export function getTrainerSpriteSrc(trainerClass, trainerName = '') {
  // Try named trainer first
  if (trainerName) {
    const stem = NAME_MAP[trainerName]
    if (stem) return `/sprites/trainers/gen3/Spr_FRLG_${stem}.png`
  }
  // Fall back to class
  const stem = CLASS_MAP[trainerClass]
  if (stem) return `/sprites/trainers/gen3/Spr_FRLG_${stem}.png`
  return null
}
