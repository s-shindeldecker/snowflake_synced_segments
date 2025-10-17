# Snowflake → LaunchDarkly Integration Guide

## For LaunchDarkly Internal Team

This document provides technical details for implementing and maintaining the Snowflake synced segments integration.

## Architecture Overview

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Snowflake  │  HTTP   │   LaunchDarkly   │  Parse  │   LaunchDarkly  │
│   Task/     │ POST    │   Integration    │   &     │    Segments     │
│  Procedure  │────────>│    Framework     │ Store   │      API        │
└─────────────┘         └──────────────────┘────────>└─────────────────┘
```

The integration uses LaunchDarkly's Integration Framework to:
1. Receive webhook POSTs from Snowflake
2. Parse the payload using the manifest configuration
3. Update LaunchDarkly segments via the internal segments API

## Key Implementation Details

### Webhook Payload Design

We chose the **separate arrays approach** (`addMemberArrayPath` and `removeMemberArrayPath`) because:
- More explicit than boolean flags
- Easier to debug (clear separation of adds vs removes)
- Matches common data warehouse patterns
- Supports incremental updates efficiently

### Manifest Configuration

#### Request Parser Paths

```json
{
  "environmentIdPath": "/environmentId",
  "contextKindPath": "/contextKind",
  "cohortIdPath": "/cohortId",
  "cohortNamePath": "/cohortName",
  "cohortUrlPath": "/cohortUrl",
  "addMemberArrayPath": "/included",
  "removeMemberArrayPath": "/excluded",
  "memberArrayParser": {
    "memberIdPath": "/contextKey"
  }
}
```

**Why these paths:**
- `/environmentId`: Customers provide client-side ID during setup
- `/contextKind`: Supports multi-context targeting (users, orgs, devices)
- `/cohortId`: Becomes the segment key in LaunchDarkly
- `/cohortName`: Displayed in LaunchDarkly UI
- `/cohortUrl`: Optional link back to Snowflake for reference
- `/included` and `/excluded`: Clear semantic meaning
- `/contextKey`: Standard LaunchDarkly context identifier

### Authentication

The integration uses LaunchDarkly's standard integration framework authentication:
- Customer provides client-side ID during integration setup
- Framework validates the environment exists and user has access
- No API keys exposed in Snowflake code

### Error Handling

The `jsonResponseBody` template provides structured error responses:

```json
{
  "status": "success|error",
  "segmentKey": "premium-users",
  "projectKey": "my-project",
  "environmentKey": "production",
  "error": {
    "message": "Segment not found",
    "code": 404
  }
}
```

This allows Snowflake procedures to:
- Log sync success/failure
- Retry on specific errors
- Alert on persistent failures

## Lessons Learned from Middleware Implementation

### API Authentication Format
- **Correct**: `Authorization: api-xxxxx` (token directly)
- **Incorrect**: `Authorization: Bearer api-xxxxx`
- Integration framework handles this automatically

### Common Error Scenarios

| Error | Cause | Customer Action |
|-------|-------|-----------------|
| 401 | Invalid environment ID | Verify client-side ID in integration config |
| 404 | Segment doesn't exist yet | First sync creates the segment automatically |
| 400 | Malformed payload | Check Snowflake procedure JSON formatting |
| 429 | Rate limit exceeded | Reduce sync frequency or batch operations |

### Version Tracking

The manifest includes version tracking for:
- Troubleshooting customer issues
- Managing breaking changes
- Deprecation notices

## Testing Strategy

### 1. Local Validation

Use the integration validation server:
```bash
# Clone integration-framework repo
git clone https://github.com/launchdarkly/integration-framework.git

# Add Snowflake integration
cp -r integration-manifest/* integration-framework/integrations/snowflake/

# Run validation server
cd integration-framework
npm install
npm run validate snowflake
```

### 2. Sample Payloads for Testing

**Basic sync (add users):**
```json
{
  "environmentId": "test-client-side-id",
  "contextKind": "user",
  "cohortId": "test-segment",
  "cohortName": "Test Segment",
  "included": [
    {"contextKey": "user-1"},
    {"contextKey": "user-2"}
  ],
  "excluded": []
}
```

**Incremental update (add and remove):**
```json
{
  "environmentId": "test-client-side-id",
  "contextKind": "user",
  "cohortId": "test-segment",
  "cohortName": "Test Segment",
  "included": [
    {"contextKey": "user-3"}
  ],
  "excluded": [
    {"contextKey": "user-1"}
  ]
}
```

**Organization context:**
```json
{
  "environmentId": "test-client-side-id",
  "contextKind": "organization",
  "cohortId": "enterprise-orgs",
  "cohortName": "Enterprise Organizations",
  "included": [
    {"contextKey": "org-123"},
    {"contextKey": "org-456"}
  ],
  "excluded": []
}
```

### 3. End-to-End Testing

1. Set up test Snowflake account
2. Configure integration in test LaunchDarkly project
3. Create stored procedure with test data
4. Verify segment creation and updates
5. Test error scenarios (invalid IDs, rate limits, etc.)

## Performance Considerations

### Batch Size Limits
- Maximum 1000 contexts per `included` array
- Maximum 1000 contexts per `excluded` array
- Snowflake procedures should batch large segments

### Recommended Sync Frequencies
- Real-time critical: Every 5-15 minutes
- Standard: Every 1-6 hours
- Large segments (>10k users): Daily

### Network Rules in Snowflake

Customers need to configure external network access:
```sql
CREATE OR REPLACE NETWORK RULE launchdarkly_access_rule
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('app.launchdarkly.com');

CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION launchdarkly_integration
  ALLOWED_NETWORK_RULES = (launchdarkly_access_rule)
  ENABLED = true;
```

## Customer Onboarding

### Required Information from Customer
1. LaunchDarkly client-side ID
2. Snowflake account identifier
3. Expected segment sizes
4. Desired sync frequency

### Common Questions

**Q: Can we sync multiple segments?**
A: Yes, create separate stored procedures or tasks for each segment.

**Q: What's the maximum segment size?**
A: No hard limit, but batch syncs for segments >10k contexts.

**Q: How do we handle deleted users?**
A: Add them to the `excluded` array in the next sync.

**Q: Can we sync custom context kinds?**
A: Yes, set the `contextKind` field to any valid LaunchDarkly context kind.

## Monitoring & Observability

### Metrics to Track
- Sync success/failure rate
- Average sync latency
- Segment size distribution
- API error rates by type

### Customer Support Debugging

When a customer reports issues:

1. **Verify integration configuration**
   - Check client-side ID is valid
   - Confirm environment exists and is accessible

2. **Check recent sync attempts**
   - Review webhook logs
   - Look for parsing errors
   - Check for rate limiting

3. **Validate payload format**
   - Ask customer for sample payload
   - Test with validation server

4. **Check segment state**
   - Verify segment exists in LaunchDarkly
   - Check current membership count
   - Review audit log for sync events

## Deployment Checklist

- [ ] Manifest JSON validated
- [ ] README documentation complete
- [ ] Logo assets created (SVG, grayscale)
- [ ] Demo video recorded
- [ ] Integration tested with validation server
- [ ] End-to-end test with real Snowflake account
- [ ] Internal documentation updated
- [ ] Support team trained
- [ ] Monitoring dashboards configured
- [ ] Launch announcement prepared

## Future Enhancements

### Potential Improvements
1. **Bi-directional sync**: Update Snowflake when segments change in LaunchDarkly
2. **Bulk operations**: Support syncing multiple segments in one request
3. **Delta compression**: Only send changes since last sync
4. **Validation API**: Pre-validate payloads before sending
5. **Sync scheduling**: Built-in scheduling instead of Snowflake tasks

### Feature Requests to Monitor
- Support for nested context attributes
- Segment targeting rules (not just membership)
- Real-time streaming via Snowflake Streams
- Integration with Snowflake Data Sharing

## Related Documentation

- [Synced Segments Capability](https://launchdarkly.com/docs/integrations/partner-integrations/synced-segments)
- [Integration Framework Repository](https://github.com/launchdarkly/integration-framework)
- [Amplitude Integration Example](https://github.com/launchdarkly/integration-framework/blob/main/integrations/amplitude/manifest.json)
- [LaunchDarkly Segments API](https://apidocs.launchdarkly.com/)

## Contact

**Integration Maintainer**: [Your team name]  
**Support Email**: [email protected]  
**Internal Slack**: #integrations-snowflake

