import { describe, expect, it } from 'vitest'
import { buildCustomSets, getDamageCalc, opponentMoveNames } from './damageCalc'

describe('getDamageCalc', () => {
  it('maps Blaze Black and Volt White to a gen-5 calc', () => {
    expect(getDamageCalc(1001)).toEqual({ gen: 5 })
    expect(getDamageCalc('1002')).toEqual({ gen: 5 })
  })

  it('has no calc for games not yet wired up', () => {
    expect(getDamageCalc(17)).toBeNull()
    expect(getDamageCalc(null)).toBeNull()
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
    const sets = buildCustomSets(playerParty, opponentParty, 'CHEREN', 21)
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
    const sets = buildCustomSets([{ species_name: 'HOOTHOOT', ivs: { atk: 0, spa: 30 } }], [], null, 18)
    expect(sets.Hoothoot['Hoothoot (yours)'].ivs).toEqual({ atk: 0, spa: 30 })
  })

  it('title-cases uppercase species and fixes punctuated names', () => {
    const sets = buildCustomSets([{ species_name: 'NIDORAN M' }], [], null, 20)
    expect(Object.keys(sets)).toEqual(['Nidoran-M'])
  })

  it('formats trainer item tokens the calc dex recognizes', () => {
    const sets = buildCustomSets([], [
      { species_name: 'ALAKAZAM', lvl: 40, held_item: 'ITEM_ORAN_BERRY' },
      { species_name: 'BEARTIC', lvl: 40, held_item: 'NeverMeltIce' },
      { species_name: 'DRILBUR', lvl: 40, held_item: 'Toxic Orb*' },
    ], 'BOSS', 40)
    expect(sets.Alakazam['BOSS Lv40'].item).toBe('Oran Berry')
    expect(sets.Beartic['BOSS Lv40'].item).toBe('Never-Melt Ice')
    expect(sets.Drilbur['BOSS Lv40'].item).toBe('Toxic Orb')
  })

  it('uses each trainer mon\'s real level, and the cap for the player', () => {
    const sets = buildCustomSets(
      [{ species_name: 'NATU' }],
      [{ species_name: 'PANSEAR', lvl: 23 }],
      'CHEREN', 21,
    )
    expect(sets.Natu['Natu (yours)'].level).toBe(21)
    expect(sets.Pansear['CHEREN Lv23'].level).toBe(23)
  })
})
