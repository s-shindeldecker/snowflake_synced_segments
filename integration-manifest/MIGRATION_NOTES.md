# Migration Notes: Middleware to Integration Framework

## Overview

This document explains the transition from the custom FastAPI middleware approach to the official LaunchDarkly Integration Framework approach for the Snowflake synced segments integration.

## Architecture Comparison

### Middleware Approach (Current Prototype)

```
Snowflake → Vercel (FastAPI) → LaunchDarkly REST API
```

**Components:**
- Custom FastAPI application (`main.py`)
- Deployed on Vercel
- Environment variables for configuration
- Manual error handling and logging
- Direct API calls to LaunchDarkly

**Advantages:**
- Full control over logic
- Easy to debug locally
- Flexible error handling
- Quick prototyping

**Disadvantages:**
- Requires hosting infrastructure
- Manual maintenance and updates
- No integration marketplace presence
- Customers must deploy and manage
- No built-in monitoring

### Integration Framework Approach (Official)

```
Snowflake → LaunchDarkly Integration Framework → LaunchDarkly Segments
```

**Components:**
- JSON manifest configuration
- LaunchDarkly-hosted webhook endpoint
- Framework-provided parsing and validation
- Built-in error handling
- Integration marketplace listing

**Advantages:**
- LaunchDarkly manages hosting
- Automatic updates and maintenance
- Listed in integrations marketplace
- Built-in monitoring and logging
- Standardized customer experience
- No infrastructure costs

**Disadvantages:**
- Less control over custom logic
- Must fit framework patterns
- Requires LaunchDarkly review process

## Key Learnings from Middleware Implementation

### 1. API Authentication

**Discovery:**
```python
# INCORRECT (tried initially)
headers = {"Authorization": f"Bearer {LD_API_KEY}"}

# CORRECT
headers = {"Authorization": f"{LD_API_KEY}"}
```

**Impact on Integration Framework:**
- Framework handles authentication automatically
- No need to expose API format to customers
- Customers only need to provide client-side ID

### 2. Error Handling Patterns

**Middleware Implementation:**
```python
if response.status_code == 404:
    raise HTTPException(
        status_code=404, 
        detail=f"Segment '{segment_key}' not found in LaunchDarkly"
    )
elif response.status_code == 401:
    raise HTTPException(
        status_code=401, 
        detail="Unauthorized: Invalid LaunchDarkly API key"
    )
```

**Integration Framework:**
- Standardized error responses
- Custom `jsonResponseBody` template
- Consistent error format across all integrations

### 3. Payload Design Evolution

**Initial Design (from middleware):**
```json
{
  "audience": "segment-key",
  "included": ["user_123"],
  "excluded": [],
  "version": 1
}
```

**Final Design (for framework):**
```json
{
  "environmentId": "client-side-id",
  "contextKind": "user",
  "cohortId": "segment-key",
  "cohortName": "Segment Name",
  "included": [{"contextKey": "user_123"}],
  "excluded": []
}
```

**Changes and Rationale:**
- `audience` → `cohortId`: Matches framework terminology
- `version` removed: Framework handles versioning
- Added `contextKind`: Supports multi-context targeting
- Added `cohortName`: Better UX in LaunchDarkly UI
- Structured context objects: More extensible

### 4. Endpoints and Routing

**Middleware Endpoints:**
```python
POST /api/snowflake-sync    # Main sync endpoint
GET  /api/segments           # List segments (debugging)
GET  /health                 # Health check
GET  /                       # API info
```

**Integration Framework:**
- Single webhook endpoint provided by framework
- No need for auxiliary endpoints
- Monitoring built into framework

## Code Reusability

### What Can Be Reused

1. **Validation Logic**
   ```python
   # From main.py - input validation patterns
   if not request.audience or not request.audience.strip():
       raise HTTPException(status_code=400, detail="audience required")
   ```
   → Inform manifest's required field definitions

2. **Error Messages**
   ```python
   # From main.py - clear error messages
   detail=f"Segment '{segment_key}' not found in project '{LD_PROJECT_KEY}'"
   ```
   → Use in `jsonResponseBody` template

3. **Documentation**
   - README.md structure and examples
   - Troubleshooting scenarios
   - Best practices section

### What Cannot Be Reused

1. **FastAPI Application Code**
   - Framework uses declarative manifest instead of imperative code
   - No Python/JavaScript execution in framework

2. **Custom Middleware Logic**
   - Framework parser is configuration-based
   - Cannot add custom transformation logic

3. **Deployment Configuration**
   - No Vercel deployment
   - No environment variable management
   - LaunchDarkly handles all hosting

## Migration Checklist

### Pre-Migration

- [x] Document all middleware endpoints and functionality
- [x] Capture error handling patterns
- [x] Document API authentication learnings
- [x] Save example payloads and responses
- [x] Review customer feedback from prototype testing

### Manifest Development

- [x] Create manifest.json with syncedSegment capability
- [x] Define request parser paths
- [x] Configure custom response template
- [x] Validate manifest structure

### Documentation

- [x] Write customer-facing README
- [x] Create integration guide for internal team
- [x] Document payload examples
- [x] Create troubleshooting guide

### Testing

- [ ] Test with integration validation server
- [ ] Verify all payload examples work
- [ ] Test error scenarios
- [ ] Validate with real Snowflake account
- [ ] End-to-end integration test

### Assets

- [ ] Create grayscale SVG logo
- [ ] Record demo video
- [ ] Capture screenshots for documentation
- [ ] Prepare marketing materials

### Submission

- [ ] Fork integration-framework repository
- [ ] Add all files to integrations/snowflake/
- [ ] Create pull request
- [ ] Email [email protected]
- [ ] Schedule walkthrough with LaunchDarkly team

## Testing Strategy

### Middleware Testing (Already Done)

```bash
# Local testing
curl -X POST http://localhost:8000/api/snowflake-sync \
  -H "Content-Type: application/json" \
  -d '{"audience": "test", "included": ["user1"], "excluded": [], "version": 1}'

# Production testing
curl -X POST https://snowflake-synced-segments.vercel.app/api/snowflake-sync \
  -H "Content-Type: application/json" \
  -d '{"audience": "test", "included": ["user1"], "excluded": [], "version": 1}'
```

### Integration Framework Testing (To Do)

```bash
# Clone and setup
git clone https://github.com/launchdarkly/integration-framework.git
cd integration-framework
npm install

# Add Snowflake integration
cp -r ../integration-manifest/* integrations/snowflake/

# Run validation server
npm run validate snowflake

# Test with curl
curl -X POST http://localhost:3000/integrations/snowflake/webhook \
  -H "Content-Type: application/json" \
  -d @payload-examples.json
```

## Timeline and Phases

### Phase 1: Prototype (Completed)
- ✅ Built FastAPI middleware
- ✅ Tested with LaunchDarkly API
- ✅ Discovered authentication format
- ✅ Validated payload structure
- ✅ Deployed to Vercel for testing

### Phase 2: Integration Framework (Current)
- ✅ Created manifest.json
- ✅ Written documentation
- ✅ Defined payload examples
- ⏳ Local validation testing
- ⏳ Logo and assets creation
- ⏳ Demo video recording

### Phase 3: Submission (Next)
- ⏳ Submit to LaunchDarkly
- ⏳ Review process
- ⏳ Beta testing with select customers
- ⏳ GA release

### Phase 4: Post-Launch
- ⏳ Monitor adoption metrics
- ⏳ Gather customer feedback
- ⏳ Iterate on documentation
- ⏳ Add advanced features

## Performance Comparison

### Middleware Performance
- **Latency**: 200-500ms (Vercel → LaunchDarkly)
- **Throughput**: Limited by Vercel serverless limits
- **Cost**: Vercel hosting fees

### Integration Framework Performance
- **Latency**: 100-300ms (LaunchDarkly internal)
- **Throughput**: LaunchDarkly's production infrastructure
- **Cost**: $0 (included in LaunchDarkly platform)

## Support Transition

### Middleware Support (Prototype)
- Direct support via Slack/email
- Manual log review in Vercel
- Custom debugging tools

### Integration Framework Support (Production)
- LaunchDarkly support team
- Built-in integration logs
- Standard troubleshooting guides
- Community forum support

## Rollout Plan

1. **Internal Testing** (Week 1-2)
   - Validate manifest with validation server
   - Test with internal LaunchDarkly projects
   - Verify all error scenarios

2. **Beta Testing** (Week 3-4)
   - Select 3-5 friendly Snowflake customers
   - Gather feedback on documentation
   - Identify edge cases

3. **GA Launch** (Week 5-6)
   - List in integrations marketplace
   - Publish announcement blog post
   - Host customer webinar
   - Update main documentation site

## Success Metrics

### Middleware Success (Prototype)
- ✅ Proof of concept validated
- ✅ API authentication figured out
- ✅ Payload format designed
- ✅ Error handling patterns established

### Integration Framework Success (Production)
- Target: 50+ customers in first quarter
- Target: 95% sync success rate
- Target: <5 support tickets per week
- Target: 4.5+ star rating in marketplace

## Conclusion

The middleware prototype served its purpose:
- Validated technical feasibility
- Discovered API authentication nuances
- Tested payload structures
- Informed documentation needs

The integration framework approach is the right choice for production:
- Scalable and maintainable
- Better customer experience
- No hosting overhead
- Official LaunchDarkly support
- Marketplace visibility

Both approaches were necessary: prototype to learn, framework to ship.

