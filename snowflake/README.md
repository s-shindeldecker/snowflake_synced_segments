# Snowflake Synced Segments -- Snowflake-Side Implementation

Sync segment membership from Snowflake tables to LaunchDarkly via the middleware API.
Changes you make to Snowflake tables (inserts, updates, deletes) are detected and
pushed as incremental updates to LaunchDarkly segments.

## Prerequisites

- **Snowflake account** with `ACCOUNTADMIN` role (or a role with privileges to create
  databases, network rules, external access integrations, and stored procedures)
- **Middleware endpoint** -- the Vercel-deployed FastAPI middleware URL
  (e.g. `https://snowflake-synced-segments.vercel.app`)
- **LaunchDarkly project** with the middleware's environment variables configured
  (`LD_API_KEY`, `LD_PROJECT_KEY`, `LD_ENV_KEY`)

## Quick Start

Run the SQL scripts in order from a Snowflake worksheet or SnowSQL session.
Each script is self-contained and idempotent (uses `CREATE OR REPLACE` / `IF NOT EXISTS`).

```
01_setup.sql            -- Database, schema, warehouse
02_network_access.sql   -- Network rule + external access integration
03_tables.sql           -- SEGMENTS, SEGMENT_MEMBERS, SYNC_LOG tables
04_sync_procedure.sql   -- Python stored procedure (sync engine)
05_task.sql             -- Scheduled Snowflake Task (optional automation)
06_seed_data.sql        -- Sample segment and members for the demo
07_demo_walkthrough.sql -- Interactive CRUD lifecycle walkthrough
```

### Step-by-step

1. Open a Snowflake worksheet and set your role to `ACCOUNTADMIN`.
2. Run `01_setup.sql` to create the database, schema, and warehouse.
3. Run `02_network_access.sql` to allow outbound HTTPS to the middleware.
4. Run `03_tables.sql` to create the three core tables.
5. Run `04_sync_procedure.sql` to create the sync stored procedure.
6. Run `05_task.sql` if you want automated scheduled syncing (optional).
7. Run `06_seed_data.sql` to populate sample data.
8. Walk through `07_demo_walkthrough.sql` step-by-step to see the full CRUD lifecycle.

## How It Works

### Tables

| Table | Purpose |
|-------|---------|
| `SEGMENTS` | One row per segment. Tracks key, name, context kind, sync version, and last sync time. |
| `SEGMENT_MEMBERS` | One row per context-in-segment. `is_active` drives include vs. exclude. |
| `SYNC_LOG` | Append-only audit trail of every sync attempt. |

### Change Detection

The sync procedure uses **timestamp-based diffing**:

- Each member row has an `updated_at` timestamp.
- Each segment tracks `last_synced_at`.
- On sync, the procedure queries members where `updated_at > last_synced_at`.
- Active members go into the `included` list; inactive members go into `excluded`.
- On the first sync (no `last_synced_at`), all active members are included.

### CRUD Lifecycle

| Operation | SQL | Sync Effect |
|-----------|-----|-------------|
| Add a member | `INSERT INTO SEGMENT_MEMBERS ...` | Sent as `included` |
| Remove a member | `UPDATE SEGMENT_MEMBERS SET is_active = FALSE ...` | Sent as `excluded` |
| Re-add a member | `UPDATE SEGMENT_MEMBERS SET is_active = TRUE ...` | Sent as `included` |
| Bulk add | `INSERT INTO SEGMENT_MEMBERS` (multiple rows) | All sent as `included` |

### Batching

The LaunchDarkly API caps at 1000 contexts per `included`/`excluded` array.
The sync procedure automatically splits large payloads into batches of 1000.

## Adapting for Your Own Segments

1. Insert your segment definition into `SEGMENTS`:
   ```sql
   INSERT INTO SEGMENTS (segment_key, segment_name, context_kind)
   VALUES ('my-segment', 'My Segment', 'user');
   ```

2. Populate `SEGMENT_MEMBERS` from your own tables:
   ```sql
   INSERT INTO SEGMENT_MEMBERS (segment_key, context_key)
   SELECT 'my-segment', user_id
   FROM my_analytics.active_users
   WHERE some_criteria = TRUE;
   ```

3. Call the sync procedure:
   ```sql
   CALL SYNC_SEGMENT_TO_LD('my-segment', 'https://your-middleware-url.vercel.app');
   ```

## Targeting the Integration Framework (Future)

When the LaunchDarkly Integration Framework submission is approved, the Snowflake code
can be pointed at the framework's webhook URL instead of the middleware. The only change
needed is the `sync_endpoint_url` parameter passed to the stored procedure. The payload
format used by the middleware (`audience`, `included`, `excluded`, `version`) would need
to be updated to the framework format (`environmentId`, `cohortId`, `contextKind`, etc.)
-- see `integration-manifest/README.md` for the framework payload specification.
