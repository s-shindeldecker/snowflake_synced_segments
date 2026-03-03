-- =============================================================================
-- 05_task.sql -- Scheduled Snowflake Task for automated segment syncing
-- =============================================================================
-- Creates a helper procedure that iterates over all segments, plus a Task that
-- calls it on a cron schedule. The task is created SUSPENDED -- resume it when
-- you are ready for automated syncing.

USE DATABASE LD_SYNC_DEMO;
USE SCHEMA SYNCED_SEGMENTS;

-- ---------------------------------------------------------------------------
-- Helper procedure: sync ALL segments in the SEGMENTS table
-- ---------------------------------------------------------------------------
CREATE OR REPLACE PROCEDURE SYNC_ALL_SEGMENTS(
    SYNC_ENDPOINT_URL VARCHAR
)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python', 'requests')
EXTERNAL_ACCESS_INTEGRATIONS = (LD_SYNC_ACCESS_INTEGRATION)
HANDLER = 'run'
AS
$$
import json

def run(session, sync_endpoint_url: str) -> str:
    """Iterate over every segment and sync each one."""
    segments = session.sql("SELECT SEGMENT_KEY FROM SEGMENTS").collect()

    if not segments:
        return json.dumps({"status": "no_segments", "message": "No segments found in SEGMENTS table"})

    results = []
    for row in segments:
        key = row["SEGMENT_KEY"]
        result_json = session.sql(
            f"CALL SYNC_SEGMENT_TO_LD('{key.replace(chr(39), chr(39)+chr(39))}', "
            f"'{sync_endpoint_url.replace(chr(39), chr(39)+chr(39))}')"
        ).collect()[0][0]
        results.append({"segment_key": key, "result": json.loads(result_json)})

    return json.dumps({"status": "complete", "segments_synced": len(results), "results": results}, default=str)
$$;

-- ---------------------------------------------------------------------------
-- Scheduled task: runs every 15 minutes (adjust the cron expression as needed)
-- ---------------------------------------------------------------------------
-- IMPORTANT: Replace the URL below with your actual middleware endpoint.
CREATE OR REPLACE TASK SYNC_SEGMENTS_TASK
    WAREHOUSE = LD_EXPORT_WH
    SCHEDULE = 'USING CRON */15 * * * * UTC'
AS
    CALL SYNC_ALL_SEGMENTS('https://snowflake-synced-segments.vercel.app');

-- The task is created in a SUSPENDED state. Resume it to start automated syncing:
--   ALTER TASK SYNC_SEGMENTS_TASK RESUME;
--
-- To pause automated syncing:
--   ALTER TASK SYNC_SEGMENTS_TASK SUSPEND;
--
-- To check task status:
--   SHOW TASKS LIKE 'SYNC_SEGMENTS_TASK';
--
-- To see task execution history:
--   SELECT *
--   FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(TASK_NAME => 'SYNC_SEGMENTS_TASK'))
--   ORDER BY SCHEDULED_TIME DESC
--   LIMIT 20;
