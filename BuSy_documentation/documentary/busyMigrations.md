# BuSy .busy Migrations

`.busy` is the persistent user data archive. Treat its internal structure as a
versioned contract between releases. New Docker images must migrate existing
archives; they must not replace `.busy` with fresh defaults.

## When To Bump Versions

- Bump `CURRENT_BUSY_FORMAT_VERSION` when changing the persisted `.busy`
  structure: required config files, manifest fields, settings/sysconfig shape,
  storage folders, renamed paths, or other archive-level contracts.
- Bump `CURRENT_DATABASE_SCHEMA_VERSION` when changing the SQLite contract:
  tables, columns, indexes, constraints, required seed rows, or data transforms
  that app code depends on.
- Do not rely on bootstrap defaults for existing users. Defaults only create
  new or missing files; migrations update old archives safely.

## Required Migration Rules

- Add ordered migrations for every version step, such as `1 -> 2`.
- Make migrations idempotent where possible: check before creating tables,
  columns, files, folders, or seed rows.
- Preserve user data. Never delete or overwrite persisted user content unless
  the migration explicitly transforms it.
- Create an external timestamp backup next to `.busy` before applying pending
  migrations.
- If a migration fails, restore the backup and fail startup with a clear error.

## Key Files

- `.busy` archive runtime and format migrations:
  `utilities/handleDocument/document.py`
- SQLite schema migrations:
  `databases/bootstrap.py`
- Database startup integration and rollback path:
  `databases/singleton.py`

