import Sprite from './Sprite'
import { TypeIconRow } from './TypeIcon'

/**
 * One slot in the PC-style Box grid. Deliberately terse: the sprite, the
 * name, the typing, and the two states that matter at a glance (in the
 * party, fallen). Everything else lives in the PokemonSummary panel that
 * opens when the tile is selected.
 */
function BoxTile({ pokemon, selected = false, inParty = false, onSelect }) {
  const { species_id, species_name, nickname, shiny, gender, status, level_met, type1, type2 } = pokemon
  const isShiny = shiny === 'True' || shiny === true
  const displayName = nickname || species_name || '???'
  const fallen = status === 'Dead'

  const className = [
    'box-tile',
    selected ? 'box-tile--selected' : '',
    fallen ? 'box-tile--fallen' : '',
    inParty ? 'box-tile--party' : '',
  ].filter(Boolean).join(' ')

  return (
    <button
      type="button"
      className={className}
      onClick={() => onSelect(pokemon)}
      aria-pressed={selected}
      title={nickname ? `${nickname} (${species_name})` : species_name}
    >
      <span className="box-tile__flags">
        {inParty && <span className="box-tile__flag box-tile__flag--party">Party</span>}
        {fallen && <span className="box-tile__flag box-tile__flag--fallen">RIP</span>}
      </span>
      <Sprite speciesId={species_id} size={56} shiny={isShiny} female={gender === 'female'} />
      <span className="box-tile__name">
        {displayName}
        {isShiny && <span className="box-tile__shiny" title="Shiny">★</span>}
      </span>
      {nickname && <span className="box-tile__species">{species_name}</span>}
      <span className="box-tile__meta">
        <TypeIconRow types={[type1, type2]} height={12} gap={3} />
        {level_met != null && <span className="box-tile__level">Lv {level_met}</span>}
      </span>
    </button>
  )
}

export default BoxTile
