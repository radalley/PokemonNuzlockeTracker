import TrainerCard from './TrainerCard'

function RivalRow({ row, gameId = null, runId = null, attemptId = null, onVictoryRecorded = null }) {
  return (
    <div style={{ marginBottom: '6px' }}>
      
      <TrainerCard
        encounterName={row.encounter_name}
        trainerName={row.trainer_name}
        trainerClass={row.trainer_class}
        trainerItems={row.trainer_items}
        encounterTitle={row.display_name}
        gameId={gameId}
        runId={runId}
        attemptId={attemptId}
        trainerId={row.event_id}
        enableBattle
        isDefeated={Boolean(row.is_defeated)}
        onVictoryRecorded={onVictoryRecorded}
      />
    </div>
  )
}

export default RivalRow