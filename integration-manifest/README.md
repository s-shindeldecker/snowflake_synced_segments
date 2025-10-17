# Snowflake Synced Segments Integration

Sync user segments from your Snowflake data warehouse directly to LaunchDarkly for powerful, data-driven feature targeting.

## Overview

The Snowflake integration allows you to:
- Automatically sync user segments from Snowflake to LaunchDarkly
- Use your existing data warehouse queries to define feature flag audiences
- Keep segment membership up-to-date with real-time or scheduled updates
- Leverage your data warehouse as the source of truth for user targeting

## Prerequisites

Before setting up this integration, you need:

1. **LaunchDarkly Account**
   - Access to a LaunchDarkly project
   - Permission to create and manage segments
   - Client-side ID for the target environment

2. **Snowflake Account**
   - Access to create and execute stored procedures
   - Permissions to create external network rules
   - Ability to send HTTP POST requests via Snowflake tasks or stored procedures

## Setup Instructions

### Step 1: Configure LaunchDarkly

1. Log in to your LaunchDarkly account
2. Navigate to **Integrations** → **Snowflake**
3. Click **Add integration**
4. Enter your **Client-side ID** for the environment where you want to sync segments
   - Find this in **Account settings** → **Projects** → Select your project → Select environment → Copy the **Client-side ID**
5. Save the integration configuration
6. Copy the **Webhook URL** provided - you'll need this for Snowflake configuration

### Step 2: Configure Snowflake

#### Create a Snowflake Stored Procedure

Create a stored procedure to format and send segment data to LaunchDarkly:

```sql
CREATE OR REPLACE PROCEDURE SYNC_SEGMENT_TO_LAUNCHDARKLY(
    SEGMENT_KEY VARCHAR,
    SEGMENT_NAME VARCHAR,
    ENVIRONMENT_ID VARCHAR,
    LAUNCHDARKLY_WEBHOOK_URL VARCHAR,
    CONTEXT_KIND VARCHAR DEFAULT 'user'
)
RETURNS VARCHAR
LANGUAGE JAVASCRIPT
AS
$$
    // Get users to include in the segment
    var included_query = `
        SELECT DISTINCT user_id 
        FROM your_users_table 
        WHERE your_segment_criteria = true
    `;
    
    var included_stmt = snowflake.createStatement({sqlText: included_query});
    var included_result = included_stmt.execute();
    
    var included_users = [];
    while (included_result.next()) {
        included_users.push({
            "contextKey": included_result.getColumnValue(1)
        });
    }
    
    // Get users to exclude from the segment
    var excluded_query = `
        SELECT DISTINCT user_id 
        FROM your_users_table 
        WHERE your_segment_criteria = false
          AND user_id IN (SELECT user_id FROM previous_segment_sync)
    `;
    
    var excluded_stmt = snowflake.createStatement({sqlText: excluded_query});
    var excluded_result = excluded_stmt.execute();
    
    var excluded_users = [];
    while (excluded_result.next()) {
        excluded_users.push({
            "contextKey": excluded_result.getColumnValue(1)
        });
    }
    
    // Prepare the payload
    var payload = {
        "environmentId": ENVIRONMENT_ID,
        "contextKind": CONTEXT_KIND,
        "cohortId": SEGMENT_KEY,
        "cohortName": SEGMENT_NAME,
        "cohortUrl": "https://app.snowflake.com/your-account",
        "included": included_users,
        "excluded": excluded_users
    };
    
    // Send to LaunchDarkly
    var http_request = snowflake.createStatement({
        sqlText: `
            SELECT PARSE_JSON(
                SYSTEM$SEND_HTTP_POST_REQUEST(
                    '${LAUNCHDARKLY_WEBHOOK_URL}',
                    '${JSON.stringify(payload)}',
                    {'Content-Type': 'application/json'}
                )
            )
        `
    });
    
    var result = http_request.execute();
    result.next();
    
    return result.getColumnValue(1);
$$;
```

#### Create a Snowflake Task for Scheduled Syncs

Create a task to automatically sync segments on a schedule:

```sql
CREATE OR REPLACE TASK SYNC_SEGMENTS_TASK
    WAREHOUSE = YOUR_WAREHOUSE
    SCHEDULE = 'USING CRON 0 */6 * * * UTC'  -- Every 6 hours
AS
CALL SYNC_SEGMENT_TO_LAUNCHDARKLY(
    'premium-users',                    -- Segment key
    'Premium Users',                    -- Segment name
    'your-client-side-id',             -- LaunchDarkly client-side ID
    'https://app.launchdarkly.com/...' -- Webhook URL from Step 1
);

-- Resume the task to start scheduling
ALTER TASK SYNC_SEGMENTS_TASK RESUME;
```

### Step 3: Verify the Integration

1. In LaunchDarkly, navigate to **Segments**
2. Look for a segment with the key you specified (e.g., `premium-users`)
3. Verify that the segment contains the expected users
4. The segment will show as "synced" and display the Snowflake logo

## Webhook Payload Format

Snowflake should send the following JSON structure to the LaunchDarkly webhook URL:

```json
{
  "environmentId": "your-client-side-id",
  "contextKind": "user",
  "cohortId": "premium-users",
  "cohortName": "Premium Users",
  "cohortUrl": "https://app.snowflake.com/your-account",
  "included": [
    {"contextKey": "user-123"},
    {"contextKey": "user-456"}
  ],
  "excluded": [
    {"contextKey": "user-789"}
  ]
}
```

### Payload Fields

| Field | Required | Description |
|-------|----------|-------------|
| `environmentId` | Yes | The LaunchDarkly client-side ID for the target environment |
| `contextKind` | No | The context kind for the segment (defaults to "user") |
| `cohortId` | Yes | Unique identifier for the segment (will become the segment key in LaunchDarkly) |
| `cohortName` | Yes | Display name for the segment |
| `cohortUrl` | No | URL back to the segment definition in Snowflake |
| `included` | Yes | Array of contexts to add to the segment |
| `excluded` | Yes | Array of contexts to remove from the segment |
| `contextKey` | Yes | The unique identifier for each context (user ID, etc.) |

## Context Kinds

LaunchDarkly supports multiple context kinds beyond just users. You can sync segments for:
- `user` (default)
- `organization`
- `device`
- Custom context kinds defined in your LaunchDarkly project

Specify the context kind in the `contextKind` field of your webhook payload.

## Best Practices

1. **Start Small**: Test with a small segment before syncing large audiences
2. **Monitor Sync Frequency**: Balance real-time needs with API rate limits
3. **Use Incremental Syncs**: Only send changes (included/excluded) rather than full segment lists
4. **Handle Errors**: Implement retry logic in your Snowflake procedures
5. **Track Sync History**: Log sync operations in Snowflake for audit purposes

## Troubleshooting

### Segment Not Appearing in LaunchDarkly

- Verify the `environmentId` matches your LaunchDarkly client-side ID
- Check that the webhook URL is correct
- Ensure the payload format matches the specification above

### Users Not Being Added/Removed

- Verify `contextKey` values match the context keys used in your LaunchDarkly flags
- Check that `contextKind` matches your flag targeting configuration
- Ensure the segment is included in your flag targeting rules

### HTTP Errors

| Status Code | Meaning | Solution |
|-------------|---------|----------|
| 400 | Bad Request | Check payload format and required fields |
| 401 | Unauthorized | Verify your LaunchDarkly configuration |
| 404 | Not Found | Check the webhook URL |
| 429 | Rate Limited | Reduce sync frequency |

## Rate Limits

LaunchDarkly's synced segments API has the following limits:
- Maximum 1000 context additions per request
- Maximum 1000 context removals per request
- Rate limits apply per account

For large segments, consider batching your sync operations.

## Support

For issues with this integration:
- LaunchDarkly support: [email protected]
- Documentation: https://docs.launchdarkly.com/integrations/snowflake
- Community: https://support.launchdarkly.com

## Example Use Cases

### 1. Premium User Targeting
Target users who have made purchases above a certain threshold:
```sql
SELECT user_id FROM purchases 
GROUP BY user_id 
HAVING SUM(amount) > 1000
```

### 2. Engagement-Based Features
Target highly engaged users based on activity metrics:
```sql
SELECT user_id FROM user_activity 
WHERE last_login_date > DATEADD(day, -7, CURRENT_DATE())
  AND session_count > 10
```

### 3. Geographic Targeting
Target users in specific regions:
```sql
SELECT user_id FROM users 
WHERE country IN ('US', 'CA', 'MX')
```

### 4. Cohort Analysis
Target users from specific signup cohorts:
```sql
SELECT user_id FROM users 
WHERE DATE_TRUNC('month', signup_date) = '2024-01-01'
```

