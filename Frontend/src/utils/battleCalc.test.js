import { describe, expect, it } from 'vitest'
import * as engine from '@smogon/calc'
import { toCalcPokemon, toCalcMove, calcMatchup, opponentMoveRows, damagePanelEnabled } from './battleCalc'

const gen = engine.Generations.get(5)

const snivyRow = {
  species_name: 'SNIVY',
  nickname: 'Kento',
  nature: 'Quiet',
  chosen_ability: 'Contrary',
  ivs: { hp: 1, atk: null, def: null, spa: null, spd: null, spe: null },
  type1: 'GRASS', type2: null,
  hp: 45, atk: 45, def: 55, spa: 45, spd: 55, spe: 63,
}

const sandileRow = {
  species_name: 'SANDILE',
  ability1: 'ABILITY_MOXIE',
  held_item: 'ITEM_ORAN_BERRY',
  lvl: 21,
  type1: 'GROUND', type2: 'DARK',
  hp: 50, atk: 72, def: 35, spa: 35, spd: 35, spe: 65,
}

describe('damagePanelEnabled', () => {
  it('gates to Blaze Black / Volt White for now', () => {
    expect(damagePanelEnabled(1001)).toBe(true)
    expect(damagePanelEnabled(1002)).toBe(true)
    expect(damagePanelEnabled(17)).toBe(false)
  })
})

describe('toCalcPokemon', () => {
  it('builds a player mon with recorded facts and 31-defaults for unrecorded IVs', () => {
    const mon = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    expect(mon.name).toBe('Snivy')
    expect(mon.level).toBe(21)
    expect(mon.ability).toBe('Contrary')
    expect(mon.nature).toBe('Quiet')
    expect(mon.ivs.hp).toBe(1)
    expect(mon.ivs.atk).toBe(31)
  })

  it('applies hack base-stat overrides (damage shifts with the buff)', () => {
    const vanilla = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    const buffed = toCalcPokemon(engine, gen, { ...snivyRow, def: 95, hp: 70 }, { level: 21, isPlayer: true })
    const attacker = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    const move = toCalcMove(engine, gen, { move_name: 'Crunch', type: 'DARK', damage_class: 'physical', power: 80 }).move
    const vsVanilla = engine.calculate(gen, attacker, vanilla, move).range()
    const vsBuffed = engine.calculate(gen, attacker, buffed, move).range()
    expect(vsBuffed[1]).toBeLessThan(vsVanilla[1])
  })

  it('builds a trainer mon with formatted ability and item', () => {
    const mon = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    expect(mon.ability).toBe('Moxie')
    expect(mon.item).toBe('Oran Berry')
    expect(mon.ivs.atk).toBe(31)
  })

  it('resolves compressed item spellings against the engine dex', () => {
    const spoon = toCalcPokemon(engine, gen, { ...sandileRow, held_item: 'TwistedSpoon' }, { level: 21, isPlayer: false })
    expect(spoon.item).toBe('Twisted Spoon')
    const ice = toCalcPokemon(engine, gen, { ...sandileRow, held_item: 'ITEM_NEVER_MELT_ICE' }, { level: 21, isPlayer: false })
    expect(ice.item).toBe('Never-Melt Ice')
    const starred = toCalcPokemon(engine, gen, { ...sandileRow, held_item: 'Toxic Orb*' }, { level: 21, isPlayer: false })
    expect(starred.item).toBe('Toxic Orb')
  })

  it('passes the recorded player gender for Rivalry math', () => {
    const mon = toCalcPokemon(engine, gen, { ...snivyRow, gender: 'female' }, { level: 21, isPlayer: true })
    expect(mon.gender).toBe('F')
  })

  it('pads a mono-typed row so a dual-typed dex species loses its second type', () => {
    const bulbaRow = { ...snivyRow, species_name: 'BULBASAUR', type1: 'GRASS', type2: null }
    const mon = toCalcPokemon(engine, gen, bulbaRow, { level: 21, isPlayer: true })
    expect(mon.types[0]).toBe('Grass')
    expect(mon.types[1]).toBe('???')
  })
})

describe('toCalcMove', () => {
  it('keeps a known move and applies a hack power override', () => {
    const { move } = toCalcMove(engine, gen, { move_name: 'Leaf Tornado', type: 'GRASS', damage_class: 'special', power: 90 })
    expect(move.bp).toBe(90)
    expect(move.type).toBe('Grass')
  })

  it('routes an unknown custom move through a stand-in that actually computes', () => {
    const { move, name } = toCalcMove(engine, gen, { move_name: 'Wood Horn', type: 'GRASS', damage_class: 'physical', power: 75 })
    expect(name).toBe('Wood Horn')
    expect(move.name).toBe('Tackle')
    expect(move.bp).toBe(75)
    expect(move.type).toBe('Grass')
    // the whole point: calculate must not throw and must deal real damage
    const mine = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    const theirs = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    const result = engine.calculate(gen, mine, theirs, move)
    expect(result.range()[1]).toBeGreaterThan(0)
  })

  it('resolves period-correct gen-5 spellings to their modern dex identity', () => {
    const { move } = toCalcMove(engine, gen, { move_name: 'Hi Jump Kick', type: 'FIGHTING', damage_class: 'physical', power: 130 })
    expect(move.name).toBe('High Jump Kick')
    expect(move.bp).toBe(130)
    const compressed = toCalcMove(engine, gen, { move_name: 'ThunderPunch', type: 'ELECTRIC', damage_class: 'physical', power: 75 })
    expect(compressed.move.name).toBe('Thunder Punch')
  })

  it('passes the attacker ability so Skill Link resolves five hits', () => {
    const rockBlast = { move_name: 'Rock Blast', type: 'ROCK', damage_class: 'physical', power: 25 }
    const withSkillLink = toCalcMove(engine, gen, rockBlast, 'Skill Link')
    const without = toCalcMove(engine, gen, rockBlast, 'Sturdy')
    expect(withSkillLink.move.hits).toBe(5)
    expect(without.move.hits).toBe(3)
  })

  it('lets Nature Power through to the engine as real damage', () => {
    const mine = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    const theirs = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    const [row] = calcMatchup(engine, gen, theirs, mine, [
      { move_name: 'Nature Power', type: 'NORMAL', damage_class: 'status', power: null },
    ])
    expect(row.status).toBeUndefined()
    expect(row.maxPct).toBeGreaterThan(0)
  })

  it('keeps fixed-damage moves on their dex identity (no zero-power reroute)', () => {
    const { move } = toCalcMove(engine, gen, { move_name: 'Night Shade', type: 'GHOST', damage_class: 'special', power: null })
    expect(move.name).toBe('Night Shade')
  })

  it('marks status moves as status', () => {
    const built = toCalcMove(engine, gen, { move_name: 'Hypnosis', type: 'PSYCHIC', damage_class: 'status', power: null })
    expect(built.status).toBe(true)
  })
})

describe('calcMatchup', () => {
  it('produces percent ranges and KO text for damaging moves', () => {
    const mine = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    const theirs = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    const rows = calcMatchup(engine, gen, theirs, mine, [
      { move_name: 'Crunch', type: 'DARK', damage_class: 'physical', power: 80 },
      { move_name: 'Sand-Attack', type: 'GROUND', damage_class: 'status', power: null },
    ])
    expect(rows).toHaveLength(2)
    expect(rows[0].maxPct).toBeGreaterThan(0)
    expect(rows[0].koText).toMatch(/KO/)
    expect(rows[1].status).toBe(true)
  })

  it('fixed damage computes from level (Night Shade at 21 into real HP)', () => {
    const mine = toCalcPokemon(engine, gen, snivyRow, { level: 21, isPlayer: true })
    const theirs = toCalcPokemon(engine, gen, sandileRow, { level: 21, isPlayer: false })
    const [row] = calcMatchup(engine, gen, mine, theirs, [
      { move_name: 'Night Shade', type: 'GHOST', damage_class: 'special', power: null },
    ])
    // 21 fixed damage into Sandile's computed max HP
    expect(row.minPct).toBe(row.maxPct)
    expect(row.minPct).toBeGreaterThan(20)
  })
})

describe('opponentMoveRows', () => {
  it('applies the four-slot rule: observed first, estimates fill the rest', () => {
    const rows = opponentMoveRows({
      observed_moves: [{ move_name: 'Crunch' }, { move_name: 'Dig' }],
      resolved_moves: [
        { move_name: 'Crunch' }, { move_name: 'Bite' }, { move_name: 'Sand Tomb' },
        { move_name: 'Torment' }, { move_name: 'Swagger' },
      ],
    })
    expect(rows.map(r => r.move_name)).toEqual(['Crunch', 'Dig', 'Bite', 'Sand Tomb'])
    expect(rows[0].seen).toBe(true)
    expect(rows[2].seen).toBeUndefined()
  })
})
