import { describe, expect, it } from 'vitest'
import { buildCalcExport, getDamageCalc } from './damageCalc'

describe('getDamageCalc', () => {
  it('maps Blaze Black and Volt White to the BB/VW calculator', () => {
    expect(getDamageCalc(1001)).toBeTruthy()
    expect(getDamageCalc('1001')).toBeTruthy()
    expect(getDamageCalc(1002).url).toBe(getDamageCalc(1001).url)
  })

  it('has no calc for games not yet wired up', () => {
    expect(getDamageCalc(17)).toBeNull()
    expect(getDamageCalc(null)).toBeNull()
  })
})

describe('buildCalcExport', () => {
  it('exports a full mon in Showdown format', () => {
    const text = buildCalcExport([{
      species_name: 'Pignite',
      nickname: 'Piggy',
      gender: 'male',
      nature: 'ADAMANT',
      chosen_ability: 'Blaze',
      ivs: { hp: 31, atk: 28, def: 20, spa: 12, spd: 15, spe: 31 },
    }], 20)
    expect(text).toBe([
      'Piggy (Pignite) (M)',
      'Level: 20',
      'Adamant Nature',
      'Ability: Blaze',
      'IVs: 31 HP / 28 Atk / 20 Def / 12 SpA / 15 SpD / 31 Spe',
    ].join('\n'))
  })

  it('keeps a recorded 0 IV and omits unrecorded slots', () => {
    const text = buildCalcExport([{
      species_name: 'Hoothoot',
      gender: 'female',
      ivs: { hp: null, atk: 0, def: null, spa: 30, spd: null, spe: null },
    }], null)
    expect(text).toBe('Hoothoot (F)\nIVs: 0 Atk / 30 SpA')
  })

  it('drops the nickname when it just repeats the species', () => {
    const text = buildCalcExport([{ species_name: 'Lillipup', nickname: 'lillipup' }], 14)
    expect(text).toBe('Lillipup\nLevel: 14')
  })

  it('formats ability tokens and separates mons with blank lines', () => {
    const text = buildCalcExport([
      { species_name: 'Drilbur', chosen_ability: 'ABILITY_SAND_RUSH' },
      { species_name: 'NIDORAN M' },
    ], 25)
    expect(text).toBe('Drilbur\nLevel: 25\nAbility: Sand Rush\n\nNidoran-M\nLevel: 25')
  })

  it('title-cases the uppercase names the species table stores', () => {
    // The calc's parser is case-sensitive: 'SNIVY' fails, 'Snivy' imports.
    const text = buildCalcExport([{ species_name: 'SNIVY', nature: 'Quiet', chosen_ability: 'Contrary', ivs: { hp: 1 } }], 21)
    expect(text).toBe('Snivy\nLevel: 21\nQuiet Nature\nAbility: Contrary\nIVs: 1 HP')
  })

  it('skips empty rows and returns an empty string for an empty party', () => {
    expect(buildCalcExport([], 20)).toBe('')
    expect(buildCalcExport([null, { species_name: '' }], 20)).toBe('')
  })
})
