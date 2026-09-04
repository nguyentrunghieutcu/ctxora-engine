# State migrations

CTXORA state migrations are ordered and executable in harness_context.storage.migrations. Version 1 creates immutable snapshot storage; version 2 adds candidate-build storage with rollback support. scripts/migrate_state.py applies the same production migration path to an explicit workspace.
