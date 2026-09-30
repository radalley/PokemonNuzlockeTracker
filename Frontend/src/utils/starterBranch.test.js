import { describe, expect, it } from 'vitest'
import { starterBranchForSpecies, starterCaptureSpecies } from './starterBranch'

describe('starterBranchForSpecies', () => {
  it('maps each trio and its evolutions', () => {
    expect(starterBranchForSpecies(495)).toBe('Grass') // Snivy
    expect(starterBranchForSpecies(498)).toBe('Fire') // Tepig
    expect(starterBranchForSpecies(503)).toBe('Water') // Samurott
    expect(starterBranchForSpecies(1)).toBe('Grass')
    expect(starterBranchForSpecies(6)).toBe('Fire')
    expect(starterBranchForSpecies('158')).toBe('Water')
  })

  it('ignores species outside the trios', () => {
    expect(starterBranchForSpecies(25)).toBeNull()
    expect(starterBranchForSpecies(10)).toBeNull()
    expect(starterBranchForSpecies(null)).toBeNull()
  })
})

describe('starterCaptureSpecies', () => {
  it('reads a caught or fallen starter from location 1', () => {
    expect(starterCaptureSpecies({ '1:0': { species_id: 498, status: 'Captured' } })).toBe(498)
    expect(starterCaptureSpecies({ '1:0': { species_id: 501, status: 'Dead' } })).toBe(501)
  })

  it('skips missed starters and other locations', () => {
    expect(starterCaptureSpecies({ '1:0': { species_id: 498, status: 'Missed' } })).toBeNull()
    expect(starterCaptureSpecies({ '10:0': { species_id: 498, status: 'Captured' } })).toBeNull()
    expect(starterCaptureSpecies({})).toBeNull()
  })
})
