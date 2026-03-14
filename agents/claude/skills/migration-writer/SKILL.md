---
name: migration-writer
description: Generate database migration files for Goose (Go) or Drizzle (D1) from schema changes
disable-model-invocation: true
---

# Migration Writer

Generate database migration files following project conventions. Auto-detects the migration tool from the project structure.

## Workflow

1. Detect migration tool:

| Signal | Tool | Migration dir |
|--------|------|---------------|
| `*.sql` files in `migrations/` + Go project | Goose | `migrations/` or `db/migrations/` |
| `drizzle.config.ts` or `drizzle/` dir | Drizzle | `drizzle/` |
| `sqlc.yaml` | sqlc (schema only) | Check for goose in same project |

2. Read existing schema:
   - For Goose: read latest migration files to understand current schema
   - For Drizzle: read `schema.ts` / `schema/` files

3. Ask what change is needed (add table, add column, modify index, etc.)

4. Generate migration:

### Goose (SQL)

```bash
# Naming convention: YYYYMMDDHHMMSS_description.sql
goose -dir migrations create description sql
```

Generate both `-- +goose Up` and `-- +goose Down` sections. The down migration must be the exact inverse.

### Drizzle

```bash
bun drizzle-kit generate
```

Or generate manually if the schema change is described rather than coded.

5. Validate:
   - SQL syntax check (parse with sqlite3 or psql depending on driver)
   - Down migration reverses up migration
   - No destructive operations without explicit user confirmation (DROP TABLE, DROP COLUMN)

## Notes

- For D1 (SQLite): no native BOOLEAN/DATETIME — use INTEGER/TEXT
- For D1: foreign keys are always enforced
- Always generate both up and down migrations
- Never auto-run migrations — generate files only
