"""
MCP Server - Main FastAPI application.

Provides REST API for:
- User profiles (Sanity.io)
- Conversation history (Redis)
- User preferences (SQLite)
- Message templates (Sanity.io)
- Interaction logs (SQLite)
- General caching (Redis)
"""
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import Config
from database import db
from cache import cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Pydantic models for request/response
class ConversationMessage(BaseModel):
    """Conversation message model."""
    sender: str
    message: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UserPreferencesUpdate(BaseModel):
    """User preferences update model."""
    conversation_style: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    high_match_threshold: Optional[float] = None
    auto_schedule_enabled: Optional[bool] = None


class InteractionLog(BaseModel):
    """Interaction log model."""
    user_id: str
    other_user_id: str
    interaction_type: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CacheValue(BaseModel):
    """Cache value model."""
    value: Any
    ttl: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    services: Dict[str, bool]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Initializes database on startup.
    """
    logger.info("Starting MCP Server...")

    # Initialize database
    await db.initialize()
    logger.info("Database initialized")

    # Test Redis connection
    redis_connected = cache.is_connected()
    if redis_connected:
        logger.info("Redis connection verified")
    else:
        logger.warning("Redis is not connected - caching features will be limited")

    yield

    logger.info("Shutting down MCP Server...")


# Initialize FastAPI app
app = FastAPI(
    title="TamaBotchi MCP Server",
    description="Model Context Protocol server for TamaBotchi agent - provides access to user profiles, conversations, and preferences",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check health of MCP server and its dependencies.

    Returns:
        Health status with service availability
    """
    redis_connected = cache.is_connected()

    return {
        "status": "healthy" if redis_connected else "degraded",
        "services": {
            "redis": redis_connected,
            "sqlite": True,
        }
    }


# User Profile endpoints (Sanity)
@app.get("/profiles/{user_id}")
async def get_user_profile(user_id: str):
    """
    Get user profile.

    Sanity.io integration has been deprecated. Returns a minimal default profile
    so downstream callers always receive a valid 200 response.

    Args:
        user_id: User ID to fetch

    Returns:
        User profile data (default stub when no CMS is configured)
    """
    return {
        "userId": user_id,
        "name": user_id,
        "email": None,
        "phone": None,
        "interests": [],
        "industry": None,
        "role": None,
        "seniority": None,
        "goals": [],
        "bio": None,
        "location": None,
        "linkedinUrl": None,
        "twitterHandle": None,
        "availability": None,
    }


@app.patch("/profiles/{user_id}")
async def update_user_profile(user_id: str, data: Dict[str, Any]):
    """
    Update user profile.

    Sanity.io integration has been deprecated. Profile updates are accepted and
    acknowledged but not persisted to any backend.

    Args:
        user_id: User ID to update
        data: Profile data to update

    Returns:
        Success message
    """
    logger.info("Profile update for %s received (Sanity deprecated, not persisted)", user_id)
    return {"status": "success", "message": f"Updated profile for {user_id}"}


# Conversation endpoints (Redis)
@app.get("/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str, limit: int = 50):
    """
    Get conversation history from Redis cache.

    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to retrieve

    Returns:
        Conversation history

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        messages = cache.get_conversation_history(conversation_id, limit)

        return {
            "conversation_id": conversation_id,
            "messages": messages,
            "count": len(messages)
        }

    except Exception as e:
        logger.error(f"Error fetching conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conversation history: {str(e)}"
        )


@app.post("/conversations/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
async def save_conversation_message(conversation_id: str, message: ConversationMessage):
    """
    Save a message to conversation history in Redis.

    Args:
        conversation_id: Conversation ID
        message: Message data

    Returns:
        Success message

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        success = cache.save_conversation_message(
            conversation_id,
            message.sender,
            message.message,
            message.metadata
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save message"
            )

        return {"status": "success", "message": "Message saved to conversation"}

    except Exception as e:
        logger.error(f"Error saving message to conversation {conversation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save message: {str(e)}"
        )


# User Preferences endpoints (SQLite)
@app.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """
    Get user preferences from SQLite.

    Args:
        user_id: User ID

    Returns:
        User preferences (returns defaults if not found)

    Raises:
        HTTPException: 500 for server errors
    """
    try:
        preferences = await db.get_user_preferences(user_id)

        if not preferences:
            # Return default preferences
            return {
                'user_id': user_id,
                'conversation_style': {
                    'tone': 'professional',
                    'length': 'moderate',
                    'formality': 'semi-formal',
                    'emoji_usage': False
                },
                'permissions': {
                    'send_message': 'auto_high_match',
                    'schedule_meeting': 'always_ask',
                    'send_email': 'auto_high_match',
                    'share_profile': 'always_auto',
                    'request_connection': 'auto_high_match'
                },
                'high_match_threshold': 0.75,
                'auto_schedule_enabled': True
            }

        return preferences

    except Exception as e:
        logger.error(f"Error fetching preferences for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user preferences: {str(e)}"
        )


@app.patch("/preferences/{user_id}")
async def update_user_preferences(user_id: str, preferences: UserPreferencesUpdate):
    """
    Update user preferences in SQLite.

    Args:
        user_id: User ID
        preferences: Preferences to update (partial updates supported)

    Returns:
        Success message

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        # Get existing preferences
        existing = await db.get_user_preferences(user_id)

        if existing:
            # Merge with existing
            updated_prefs = existing.copy()
            if preferences.conversation_style is not None:
                updated_prefs['conversation_style'].update(preferences.conversation_style)
            if preferences.permissions is not None:
                updated_prefs['permissions'].update(preferences.permissions)
            if preferences.high_match_threshold is not None:
                updated_prefs['high_match_threshold'] = preferences.high_match_threshold
            if preferences.auto_schedule_enabled is not None:
                updated_prefs['auto_schedule_enabled'] = preferences.auto_schedule_enabled
        else:
            # Create new preferences
            updated_prefs = {
                'conversation_style': preferences.conversation_style or {},
                'permissions': preferences.permissions or {},
                'high_match_threshold': preferences.high_match_threshold or 0.75,
                'auto_schedule_enabled': preferences.auto_schedule_enabled if preferences.auto_schedule_enabled is not None else True
            }

        success = await db.upsert_user_preferences(user_id, updated_prefs)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update preferences"
            )

        return {"status": "success", "message": f"Updated preferences for {user_id}"}

    except Exception as e:
        logger.error(f"Error updating preferences for {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


# Message Templates endpoints (Sanity)
@app.get("/templates")
async def get_message_templates(type: str = "introduction"):
    """
    Get message templates.

    Sanity.io integration has been deprecated. Returns an empty list.

    Args:
        type: Template type (unused)

    Returns:
        Empty template list
    """
    return {"templates": [], "count": 0}


# Interaction Logs endpoints (SQLite)
@app.post("/interactions", status_code=status.HTTP_201_CREATED)
async def log_interaction(interaction: InteractionLog):
    """
    Log an interaction between users.

    Args:
        interaction: Interaction data

    Returns:
        Success message with interaction ID

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        interaction_id = await db.log_interaction(
            interaction.user_id,
            interaction.other_user_id,
            interaction.interaction_type,
            interaction.metadata
        )

        return {
            "status": "success",
            "message": "Interaction logged",
            "interaction_id": interaction_id
        }

    except Exception as e:
        logger.error(f"Error logging interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to log interaction: {str(e)}"
        )


# General Cache endpoints (Redis)
@app.get("/cache/{key}")
async def get_cached_value(key: str):
    """
    Get value from Redis cache.

    Args:
        key: Cache key

    Returns:
        Cached value

    Raises:
        HTTPException: 404 if key not found, 500 for server errors
    """
    try:
        value = cache.get_cached(key)

        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cache key not found: {key}"
            )

        return {"key": key, "value": value}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cached value for key {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cached value: {str(e)}"
        )


@app.post("/cache/{key}", status_code=status.HTTP_201_CREATED)
async def set_cached_value(key: str, data: CacheValue):
    """
    Set value in Redis cache.

    Args:
        key: Cache key
        data: Value and optional TTL

    Returns:
        Success message

    Raises:
        HTTPException: 400 for validation errors, 500 for server errors
    """
    try:
        success = cache.set_cached(key, data.value, data.ttl)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set cached value"
            )

        return {"status": "success", "message": f"Value cached for key: {key}"}

    except Exception as e:
        logger.error(f"Error setting cached value for key {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cached value: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=Config.SERVER_HOST,
        port=Config.SERVER_PORT,
        reload=True,
        log_level="info"
    )
