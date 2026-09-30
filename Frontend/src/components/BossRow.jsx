import TrainerCard from './TrainerCard'

function BossRow({ row, gameId = null, generation = null, runId = null, attemptId = null, onVictoryRecorded = null, attemptEnded = false }) {
  // is_level_cap comes from event_bosses; the event_type string list is the
  // fallback for rows predating the flag.
  const shouldShowLevelCap = row.is_level_cap != null
    ? Boolean(row.is_level_cap)
    : ['gym leader', 'elite four', 'champion'].includes(
        String(row.event_type || '').trim().toLowerCase()
      )

  return (
    <div style={{ marginBottom: '14px', border: '1px solid var(--border-strong)', borderRadius: '12px', overflow: 'hidden', background: 'var(--surface)' }}>
      <TrainerCard
        encounterName={row.encounter_name}
        trainerName={row.trainer_name}
        trainerClass={row.trainer_class}
        trainerPic={row.trainer_pic}
        hideClass
        trainerItems={row.trainer_items}
        encounterTitle={row.display_name}
        showLevelCap={shouldShowLevelCap}
        levelCap={row.level_cap}
        typeFocus={row.type_focus}
        gameId={gameId}
        generation={generation}
        versionGroupId={row.version_group_id}
        runId={runId}
        attemptId={attemptId}
        trainerId={row.event_id}
        bossEventId={row.boss_event_id}
        badgeId={row.badge_id}
        enableBattle
        isDefeated={Boolean(row.is_defeated)}
        onVictoryRecorded={onVictoryRecorded}
        attemptEnded={attemptEnded}
        battleType={row.battle_type}
      />
    </div>
  )
}

export default BossRow
