BEGIN;

-- Ensure canonical IDs can be targeted by ON CONFLICT.
CREATE UNIQUE INDEX IF NOT EXISTS uq_canon_locations_canonical_location_id
    ON canon_locations (canonical_location_id);

-- Seed canon_locations from locations without creating duplicates.
-- Empty canonical names fall back to location_name.
INSERT INTO canon_locations (canonical_location_id, canonical_location_name)
SELECT DISTINCT
    l.canonical_location_id,
    COALESCE(NULLIF(TRIM(l.canonical_location_name), ''), l.location_name) AS canonical_location_name
FROM locations l
WHERE l.canonical_location_id IS NOT NULL
ON CONFLICT (canonical_location_id) DO UPDATE
SET canonical_location_name = EXCLUDED.canonical_location_name
WHERE canon_locations.canonical_location_name IS DISTINCT FROM EXCLUDED.canonical_location_name;

COMMIT;
