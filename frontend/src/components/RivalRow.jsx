function RivalRow({ row }) {
  return (
    <div>
      <p>⚔️ {row.display_name} — {row.event_type}</p>
    </div>
  )
}

export default RivalRow