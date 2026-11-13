-- New databases bootstrap metadata; apply reviewed schema migrations for upgrades.
CREATE INDEX IF NOT EXISTS scenario_profile_idx ON service_scenarios (profile_id);
CREATE INDEX IF NOT EXISTS note_run_status_idx ON capacity_notes (run_id,status);
