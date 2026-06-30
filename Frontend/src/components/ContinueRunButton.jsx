import { useMemo, useState } from 'react'
import Sprite from './Sprite'

function getGameLogoSrc(gameName) {
  return `/sprites/Game Logos/Pokemon_${String(gameName || '').replace(/\s+/g, '_')}.png`
}

function ContinueRunButton({ run, onContinue }) {
  const [failedLogoKey, setFailedLogoKey] = useState('')
  const logoKey = `${run.run_id}:${run.game_name}`
  const logoFailed = failedLogoKey === logoKey
  const partyBySlot = useMemo(() => {
    const slots = new Map()
    ;(run.party || []).forEach((member, index) => {
      slots.set(Number(member.party_slot || index + 1), member)
    })
    return slots
  }, [run.party])
  const badgeIds = useMemo(
    () => Array.from(new Set((run.badges || []).map(Number).filter(Number.isInteger))).sort((a, b) => a - b),
    [run.badges]
  )

  return (
    <button
      type="button"
      className="continue-run-button"
      onClick={onContinue}
      aria-label={`Continue ${run.run_name}, attempt ${run.attempt_number}`}
    >
      <div className="continue-run-button__game">
        {!logoFailed ? (
          <img
            src={getGameLogoSrc(run.game_name)}
            alt={`Pokemon ${run.game_name}`}
            onError={() => setFailedLogoKey(logoKey)}
          />
        ) : (
          <span>{run.game_name}</span>
        )}
      </div>

      <div className="continue-run-button__details">
        <span className="continue-run-button__label">Continue</span>
        <strong>{run.run_name}</strong>
        <span className="continue-run-button__attempt">Attempt {run.attempt_number}</span>
        <div className="continue-run-button__badges" aria-label="Badges earned">
          {badgeIds.length ? badgeIds.map(badgeId => (
            <img key={badgeId} src={`/sprites/Badges/${badgeId}.png`} alt={`Badge ${badgeId}`} />
          )) : (
            <span>No badges earned</span>
          )}
        </div>
      </div>

      <div className="continue-run-button__party" aria-label="Current party">
        {Array.from({ length: 6 }, (_, index) => {
          const member = partyBySlot.get(index + 1)
          return (
            <span key={index} className={`continue-run-button__party-slot${member ? ' is-filled' : ''}`}>
              {member && (
                <Sprite
                  speciesId={member.species_id}
                  size={32}
                  shiny={member.shiny === true || member.shiny === 'True'}
                  alt={member.nickname || member.species_name || ''}
                />
              )}
            </span>
          )
        })}
      </div>
    </button>
  )
}

export default ContinueRunButton
