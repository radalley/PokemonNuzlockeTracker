import { describe, expect, it } from 'vitest'
import { buildCustomSets, calcMoveName, formatDexPatch, getDamageCalc, mergeCustomSets, opponentMoveNames } from './damageCalc'

describe('getDamageCalc', () => {
  it('maps Blaze Black and Volt White to a gen-5 calc with their title art', () => {
    expect(getDamageCalc(1001)).toEqual({ gen: 5, gameName: 'Blaze Black' })
    expect(getDamageCalc('1002')).toEqual({ gen: 5, gameName: 'Volt White' })
  })

  it('has no calc for games not yet wired up', () => {
    expect(getDamageCalc(17)).toBeNull()
    expect(getDamageCalc(null)).toBeNull()
  })
})

describe('calcMoveName', () => {
  it('title-cases and maps period spellings to the calc dex names', () => {
    expect(calcMoveName('MUD_SLAP')).toBe('Mud Slap')
    expect(calcMoveName('mud-slap')).toBe('Mud-Slap')
    expect(calcMoveName('Hi Jump Kick')).toBe('High Jump Kick')
    expect(calcMoveName('Faint Attack')).toBe('Feint Attack')
  })
})

describe('formatDexPatch', () => {
  it('maps server override rows into the calculator data shapes', () => {
    const patch = formatDexPatch({
      generation: 5,
      species: {
        'SERPERIOR': { stats: { hp: 82, atk: 75, def: 95, spa: 75, spd: 95, spe: 113 }, ability: 'Contrary' },
        'FARFETCHD': { types: ['fighting', 'flying'] },
      },
      moves: {
        'Cut': { power: 60, type: 'grass', damage_class: 'physical' },
        'Hi Jump Kick': { power: 130, type: 'fighting', damage_class: 'physical' },
      },
    })
    expect(patch.generation).toBe(5)
    expect(patch.species.Serperior).toEqual({
      bs: { hp: 82, at: 75, df: 95, sa: 75, sd: 95, sp: 113 },
      ability: 'Contrary',
    })
    expect(patch.species['Farfetch’d']).toEqual({ types: ['Fighting', 'Flying'] })
    expect(patch.moves.Cut).toEqual({ bp: 60, type: 'Grass', category: 'Physical' })
    expect(patch.moves['High Jump Kick'].bp).toBe(130)
  })

  it('produces an empty patch for vanilla payloads', () => {
    const patch = formatDexPatch({ generation: 5, species: {}, moves: {} })
    expect(patch.species).toEqual({})
    expect(patch.moves).toEqual({})
  })
})

describe('opponentMoveNames', () => {
  it('applies the four-slot rule: observed first, estimates fill the rest', () => {
    const names = opponentMoveNames({
      observed_moves: [{ move_name: 'Crunch' }, { move_name: 'Dig' }],
      resolved_moves: [
        { move_name: 'Crunch' }, { move_name: 'Bite' }, { move_name: 'Sand Tomb' },
        { move_name: 'Torment' }, { move_name: 'Swagger' },
      ],
    })
    expect(names).toEqual(['Crunch', 'Dig', 'Bite', 'Sand Tomb'])
  })
})

describe('buildCustomSets', () => {
  const playerParty = [{
    species_name: 'SNIVY',
    nickname: 'Kento',
    gender: 'male',
    nature: 'QUIET',
    chosen_ability: 'Contrary',
    ivs: { hp: 1, atk: null, def: null, spa: null, spd: null, spe: null },
  }]
  const opponentParty = [{
    species_name: 'SANDILE',
    lvl: 21,
    ability1: 'ABILITY_MOXIE',
    held_item: 'TwistedSpoon',
    resolved_moves: [{ move_name: 'Crunch' }, { move_name: 'Sand Tomb' }],
    observed_moves: [],
  }]

  it('builds both teams in the calculator storage shape', () => {
    const { sets } = buildCustomSets(playerParty, opponentParty, 'CHEREN', 21)
    expect(sets.Snivy['Kento (yours)']).toEqual({
      level: 21,
      nature: 'Quiet',
      ability: 'Contrary',
      gender: 'M',
      ivs: { hp: 1 },
      moves: [],
      isCustomSet: true,
    })
    expect(sets.Sandile['CHEREN Lv21']).toEqual({
      level: 21,
      ability: 'Moxie',
      item: 'Twisted Spoon',
      ivs: {},
      moves: ['Crunch', 'Sand Tomb'],
      isCustomSet: true,
    })
  })

  it('keeps a recorded 0 IV and drops unrecorded slots', () => {
    const { sets } = buildCustomSets([{ species_name: 'HOOTHOOT', ivs: { atk: 0, spa: 30 } }], [], null, 18)
    expect(sets.Hoothoot['Hoothoot (yours)'].ivs).toEqual({ atk: 0, spa: 30 })
  })

  it('title-cases uppercase species and fixes punctuated names', () => {
    const { sets } = buildCustomSets([{ species_name: 'NIDORAN M' }], [], null, 20)
    expect(Object.keys(sets)).toEqual(['Nidoran-M'])
  })

  it('formats trainer item tokens the calc dex recognizes', () => {
    const { sets } = buildCustomSets([], [
      { species_name: 'ALAKAZAM', lvl: 40, held_item: 'ITEM_ORAN_BERRY' },
      { species_name: 'BEARTIC', lvl: 40, held_item: 'NeverMeltIce' },
      { species_name: 'DRILBUR', lvl: 40, held_item: 'Toxic Orb*' },
    ], 'BOSS', 40)
    expect(sets.Alakazam['BOSS Lv40'].item).toBe('Oran Berry')
    expect(sets.Beartic['BOSS Lv40'].item).toBe('Never-Melt Ice')
    expect(sets.Drilbur['BOSS Lv40'].item).toBe('Toxic Orb')
  })

  it('uses each trainer mon\'s real level, and the cap for the player', () => {
    const { sets } = buildCustomSets(
      [{ species_name: 'NATU' }],
      [{ species_name: 'PANSEAR', lvl: 23 }],
      'CHEREN', 21,
    )
    expect(sets.Natu['Natu (yours)'].level).toBe(21)
    expect(sets.Pansear['CHEREN Lv23'].level).toBe(23)
  })

  it('returns both teams in party order for the calc handoff and party bar', () => {
    const { playerSets, opponentSets } = buildCustomSets(
      [{ ...playerParty[0], species_id: 495 }],
      [{ ...opponentParty[0], species_id: 551 }],
      'CHEREN', 21,
    )
    expect(playerSets).toEqual([{
      id: 'Snivy (Kento (yours))',
      label: 'Kento',
      sprite: '/sprites/Standard/495.png',
    }])
    expect(opponentSets).toEqual([{
      id: 'Sandile (CHEREN Lv21)',
      label: 'Sandile L21',
      sprite: '/sprites/Standard/551.png',
    }])
  })

  it('uses the shiny sprite for a shiny party member', () => {
    const { playerSets } = buildCustomSets(
      [{ species_name: 'NATU', species_id: 177, shiny: true }], [], null, 20,
    )
    expect(playerSets[0].sprite).toBe('/sprites/Shiny/177.png')
  })
})

describe('mergeCustomSets', () => {
  it('keeps moves saved onto a (yours) set across a reseed', () => {
    const existing = {
      Snivy: { 'Kento (yours)': { level: 20, moves: ['Leaf Tornado', 'Leech Seed'], isCustomSet: true } },
    }
    const fresh = {
      Snivy: { 'Kento (yours)': { level: 21, moves: [], isCustomSet: true } },
    }
    const merged = mergeCustomSets(existing, fresh)
    expect(merged.Snivy['Kento (yours)'].level).toBe(21)
    expect(merged.Snivy['Kento (yours)'].moves).toEqual(['Leaf Tornado', 'Leech Seed'])
  })

  it('always takes fresh trainer moves and drops stale Lockley sets', () => {
    const existing = {
      Sandile: { 'CHEREN Lv21': { level: 21, moves: ['Old Move'] } },
      Drilbur: { 'GHOST Lv30': { level: 30, moves: [] } },
      Excadrill: { 'My Own Import': { level: 50, moves: ['Earthquake'] } },
    }
    const fresh = {
      Sandile: { 'CHEREN Lv23': { level: 23, moves: ['Crunch'] } },
    }
    const merged = mergeCustomSets(existing, fresh)
    expect(merged.Sandile).toEqual({ 'CHEREN Lv23': { level: 23, moves: ['Crunch'] } })
    expect(merged.Drilbur).toBeUndefined()
    expect(merged.Excadrill['My Own Import'].moves).toEqual(['Earthquake'])
  })
})
