import os
import logging
from typing import Dict, List, Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Snowflake → LaunchDarkly Sync API", version="1.0.2")

# Environment variables
LD_API_KEY = os.getenv("LD_API_KEY")
LD_PROJECT_KEY = os.getenv("LD_PROJECT_KEY")
LD_ENV_KEY = os.getenv("LD_ENV_KEY")

# Validate required environment variables (only in production)
if not all([LD_API_KEY, LD_PROJECT_KEY, LD_ENV_KEY]):
    logger.warning("Missing required environment variables: LD_API_KEY, LD_PROJECT_KEY, LD_ENV_KEY")
    logger.warning("Running in test mode - LaunchDarkly API calls will fail")

class SnowflakeSyncRequest(BaseModel):
    audience: str = Field(..., description="Audience/segment name")
    included: List[str] = Field(..., description="List of included user IDs")
    excluded: List[str] = Field(default_factory=list, description="List of excluded user IDs")
    version: int = Field(..., description="Version number for the sync")

class SyncResponse(BaseModel):
    status: str
    ld_response: str
    count_included: int
    count_excluded: int

@app.post("/api/snowflake-sync", response_model=SyncResponse)
async def sync_snowflake_to_launchdarkly(request: SnowflakeSyncRequest) -> SyncResponse:
    """
    Sync Snowflake segment data to LaunchDarkly
    """
    try:
        # Validate input
        if not request.audience or not request.audience.strip():
            raise HTTPException(status_code=400, detail="audience field is required and cannot be empty")
        
        if not isinstance(request.included, list):
            raise HTTPException(status_code=400, detail="included must be a list")
        
        if not isinstance(request.excluded, list):
            raise HTTPException(status_code=400, detail="excluded must be a list")
        
        if not isinstance(request.version, int) or request.version < 1:
            raise HTTPException(status_code=400, detail="version must be a positive integer")
        
        # Validate segment key format (basic validation)
        segment_key = request.audience.strip()
        if not segment_key.replace('-', '').replace('_', '').isalnum():
            raise HTTPException(
                status_code=400, 
                detail="audience (segment key) must contain only alphanumeric characters, hyphens, and underscores"
            )
        
        # segment_key is already set from validation above
        
        # Prepare LaunchDarkly API call
        ld_url = f"https://app.launchdarkly.com/api/v2/segments/{LD_PROJECT_KEY}/{LD_ENV_KEY}/{segment_key}/sync"
        
        headers = {
            "Authorization": f"Bearer {LD_API_KEY}",
            "Content-Type": "application/json",
            "LD-API-Version": "beta"
        }
        
        payload = {
            "included": request.included,
            "excluded": request.excluded,
            "version": request.version
        }
        
        logger.info(f"Syncing to LaunchDarkly: {segment_key} with {len(request.included)} included, {len(request.excluded)} excluded")
        
        # Check if we have valid credentials for LaunchDarkly
        if not all([LD_API_KEY, LD_PROJECT_KEY, LD_ENV_KEY]):
            logger.warning("Missing LaunchDarkly credentials - returning mock response")
            logger.warning(f"LD_API_KEY: {'SET' if LD_API_KEY else 'NOT SET'}")
            logger.warning(f"LD_PROJECT_KEY: {'SET' if LD_PROJECT_KEY else 'NOT SET'}")
            logger.warning(f"LD_ENV_KEY: {'SET' if LD_ENV_KEY else 'NOT SET'}")
            return SyncResponse(
                status="ok",
                ld_response="Mock response - LaunchDarkly credentials not configured",
                count_included=len(request.included),
                count_excluded=len(request.excluded)
            )
        
        # Make the API call to LaunchDarkly
        logger.info(f"Making request to LaunchDarkly: {ld_url}")
        logger.info(f"Headers: {headers}")
        logger.info(f"Payload: {payload}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(ld_url, json=payload, headers=headers)
            
            logger.info(f"LaunchDarkly response status: {response.status_code}")
            logger.info(f"LaunchDarkly response text: {response.text}")
            
            if response.status_code == 200:
                logger.info(f"Successfully synced segment {segment_key} to LaunchDarkly")
                return SyncResponse(
                    status="ok",
                    ld_response="Segment updated successfully",
                    count_included=len(request.included),
                    count_excluded=len(request.excluded)
                )
            elif response.status_code == 404:
                logger.error(f"Segment not found: {segment_key}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"Segment '{segment_key}' not found in LaunchDarkly project '{LD_PROJECT_KEY}'"
                )
            elif response.status_code == 401:
                logger.error(f"Unauthorized: Invalid API key or insufficient permissions")
                raise HTTPException(
                    status_code=401, 
                    detail="Unauthorized: Invalid LaunchDarkly API key or insufficient permissions"
                )
            elif response.status_code == 403:
                logger.error(f"Forbidden: API key lacks required permissions")
                raise HTTPException(
                    status_code=403, 
                    detail="Forbidden: API key lacks required permissions for this operation"
                )
            else:
                logger.error(f"LaunchDarkly API error: {response.status_code} - {response.text}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"LaunchDarkly API error: {response.status_code} - {response.text}"
                )
                
    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling LaunchDarkly: {str(e)}")
        raise HTTPException(status_code=500, detail="Error communicating with LaunchDarkly")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "snowflake-ld-sync"}

@app.get("/api/segments")
async def list_segments():
    """
    List available segments in LaunchDarkly project
    This is helpful for debugging and finding valid segment keys
    """
    if not all([LD_API_KEY, LD_PROJECT_KEY, LD_ENV_KEY]):
        return {
            "error": "LaunchDarkly credentials not configured",
            "message": "Set LD_API_KEY, LD_PROJECT_KEY, and LD_ENV_KEY environment variables"
        }
    
    try:
        # Get segments from LaunchDarkly
        ld_url = f"https://app.launchdarkly.com/api/v2/segments/{LD_PROJECT_KEY}/{LD_ENV_KEY}"
        headers = {
            "Authorization": f"Bearer {LD_API_KEY}",
            "Content-Type": "application/json",
            "LD-API-Version": "beta"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(ld_url, headers=headers)
            
            if response.status_code == 200:
                segments = response.json()
                return {
                    "status": "ok",
                    "project": LD_PROJECT_KEY,
                    "environment": LD_ENV_KEY,
                    "segments": [{"key": seg.get("key"), "name": seg.get("name")} for seg in segments.get("items", [])]
                }
            else:
                return {
                    "error": f"LaunchDarkly API error: {response.status_code}",
                    "message": response.text
                }
                
    except Exception as e:
        return {
            "error": "Failed to fetch segments",
            "message": str(e)
        }

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Snowflake → LaunchDarkly Sync API",
        "version": app.version,
        "endpoints": {
            "sync": "/api/snowflake-sync",
            "segments": "/api/segments",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
