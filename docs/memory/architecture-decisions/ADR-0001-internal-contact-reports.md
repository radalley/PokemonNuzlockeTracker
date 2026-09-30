# ADR-0001: Internal Contact Reports

- Status: Accepted
- Scope: Contact and user-submitted data corrections

## Decision

Contact submissions are persisted in Lockley's own `contact_reports` table and
reviewed through the admin reports page. Users do not need to provide an email,
and the application does not generate one inbound email per report.

Reports include hidden application context such as `game_id`, `user_id`, and
`version_group_id`. Supported types include bug, missing information, incorrect
information, and general contact. Admin reporting supports status, game,
version, generation, and type-oriented statistics.

## Evidence

- Backend routes: `/api/contact-report`, `/api/admin/contact-reports`
- Backend ownership: `Backend/api.py`, `Backend/backend.py`
- Frontend ownership: `Frontend/src/components/ContactButton.jsx`,
  `Frontend/src/pages/AdminReports.jsx`
