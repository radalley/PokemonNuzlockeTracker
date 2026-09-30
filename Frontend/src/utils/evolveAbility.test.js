import { describe, expect, it, vi } from 'vitest'
// api.js builds the Supabase client, which needs env CI does not have.
vi.mock('./api', () => ({ apiFetch: vi.fn() }))
import { evolvedAbility } from './evolveAbility'

const tepig = [{ name: 'Blaze', slot: 1 }, { name: 'Thick Fat', slot: 3 }]
const pignite = [{ name: 'Blaze', slot: 1 }, { name: 'Thick Fat', slot: 3 }]
const nincada = [{ name: 'Compound Eyes', slot: 1 }, { name: 'Run Away', slot: 3 }]
const ninjask = [{ name: 'Speed Boost', slot: 1 }, { name: 'Infiltrator', slot: 3 }]
const twoSlot = [{ name: 'Guts', slot: 1 }, { name: 'Sheer Force', slot: 2 }]
const oneRepeated = [{ name: 'Iron Fist', slot: 1 }]

describe('evolvedAbility', () => {
  it('keeps an ability both stages share', () => {
    expect(evolvedAbility('Blaze', tepig, pignite)).toBe('Blaze')
  })

  it('switches to the new species ability in the same slot', () => {
    expect(evolvedAbility('Compound Eyes', nincada, ninjask)).toBe('Speed Boost')
    expect(evolvedAbility('Run Away', nincada, ninjask)).toBe('Infiltrator')
  })

  it('matches stored names loosely', () => {
    expect(evolvedAbility('ABILITY_COMPOUND_EYES', nincada, ninjask)).toBe('Speed Boost')
  })

  it('maps slot 2 onto a species whose two slots repeat', () => {
    expect(evolvedAbility('Sheer Force', twoSlot, oneRepeated)).toBe('Iron Fist')
  })

  it('keeps a hand-typed ability and a slot the new species lacks', () => {
    expect(evolvedAbility('Levitate', nincada, ninjask)).toBe('Levitate')
    expect(evolvedAbility('Thick Fat', tepig, oneRepeated)).toBe('Thick Fat')
    expect(evolvedAbility('Blaze', tepig, [])).toBe('Blaze')
  })

  it('leaves a blank ability blank', () => {
    expect(evolvedAbility('', tepig, pignite)).toBe('')
    expect(evolvedAbility(null, tepig, pignite)).toBe('')
  })
})
