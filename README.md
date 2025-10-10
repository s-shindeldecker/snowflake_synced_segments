# Snowflake → LaunchDarkly Sync API

A FastAPI application that receives POST requests from Snowflake and forwards those changes to LaunchDarkly's Synced Segments API.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your LaunchDarkly credentials
```

3. Run locally:
```bash
python main.py
```

The API will be available at `http://127.0.0.1:8000`

## Environment Variables

- `LD_API_KEY`: LaunchDarkly API Access Token
- `LD_PROJECT_KEY`: LaunchDarkly project key
- `LD_ENV_KEY`: LaunchDarkly environment key
- `LD_SEGMENT_KEY`: Default segment name (defaults to "snowflake_test_segment")

## API Endpoints

### POST /api/snowflake-sync

Syncs Snowflake segment data to LaunchDarkly.

**Request Body:**
```json
{
  "audience": "snowflake_test_segment",
  "included": ["user_123", "user_456"],
  "excluded": [],
  "version": 1
}
```

**Response:**
```json
{
  "status": "ok",
  "ld_response": "Segment updated",
  "count_included": 2,
  "count_excluded": 0
}
```

### GET /health

Health check endpoint.

### GET /

Root endpoint with API information.

## Testing

Test the API with curl:

```bash
curl -X POST http://127.0.0.1:8000/api/snowflake-sync \
  -H "Content-Type: application/json" \
  -d '{"audience": "snowflake_test_segment", "included": ["user_123"], "excluded": [], "version": 1}'
```

## Deployment to Vercel

1. Set environment variables in Vercel dashboard
2. Deploy using Vercel CLI or GitHub integration
3. The `vercel.json` file is configured for Python runtime

## Error Handling

- **400**: Invalid input data
- **500**: LaunchDarkly API errors or internal server errors

The API includes comprehensive logging and error handling for robust operation.
