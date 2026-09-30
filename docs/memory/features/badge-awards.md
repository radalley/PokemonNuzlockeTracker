# Badge Awards

Scripted trainer rows carry both trainer identity and event identity. A victory
request sends the event ID so the backend can validate the run's game/version
context and derive the configured badge. The backend is authoritative for
authenticated awards; guest storage mirrors the same first-victory semantics.
