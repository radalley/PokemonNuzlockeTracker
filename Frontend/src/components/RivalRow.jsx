import TrainerCard from './TrainerCard'

function RivalRow({ row, gameId = null, runId = null, attemptId = null, onVictoryRecorded = null }) {
  return (
    <div style={{ marginBottom: '14px' }}>
      
      <TrainerCard
        encounterName={row.encounter_name}
        trainerName={row.trainer_name}
        trainerClass={row.trainer_class}
        trainerPic={row.trainer_pic}
        hideClass
        trainerItems={row.trainer_items}
        encounterTitle={row.display_name}
        gameId={gameId}
        versionGroupId={row.version_group_id}
        runId={runId}
        attemptId={attemptId}
        trainerId={row.event_id}
        bossEventId={row.boss_event_id}
        badgeId={row.badge_id}
        enableBattle
        isDefeated={Boolean(row.is_defeated)}
        onVictoryRecorded={onVictoryRecorded}
      />
    </div>
  )
}

export default RivalRow
