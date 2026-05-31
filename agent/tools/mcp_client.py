"""
MCP Client for interacting with the MCP server.
Handles all communication with Sanity.io, Redis, and SQLite via MCP server.
"""
import requests
from typing import Optional, List, Any, Dict
import logging

from config import Config
from tama_types import (
    UserProfile,
    UserPreferences,
    ConversationMessage,
    MessageTemplate,
)
from exceptions import (
    MCPConnectionError,
    MCPTimeoutError,
    MCPNotFoundError,
    MCPValidationError,
    MCPError,
)

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Client for MCP server operations.

    The MCP server provides access to:
    - User profiles (Sanity.io)
    - Conversation history (Redis)
    - User preferences (SQLite)
    - Message templates (Sanity.io)
    - Interaction logs (SQLite)
    """

    def __init__(self, server_url: Optional[str] = None, timeout: int = 10):
        """
        Initialize MCP client.

        Args:
            server_url: MCP server URL, defaults to config value
            timeout: Request timeout in seconds

        Raises:
            ConfigurationError: If server URL not provided and not in config
        """
        self.server_url = server_url or Config.MCP_SERVER_URL
        self.timeout = timeout

        if not self.server_url:
            raise MCPConnectionError("MCP server URL not configured")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> requests.Response:
        """
        Make HTTP request to MCP server with proper error handling.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            json_data: JSON request body
            params: Query parameters

        Returns:
            Response object

        Raises:
            MCPConnectionError: Cannot connect to server
            MCPTimeoutError: Request timed out
            MCPNotFoundError: Resource not found (404)
            MCPValidationError: Validation error (400)
            MCPError: Other server errors
        """
        url = f"{self.server_url}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                params=params,
                timeout=self.timeout
            )

            # Handle specific status codes
            if response.status_code == 404:
                raise MCPNotFoundError(f"Resource not found: {endpoint}")

            if response.status_code == 400:
                error_detail = response.text or "Validation error"
                raise MCPValidationError(f"Invalid request to {endpoint}: {error_detail}")

            if response.status_code >= 500:
                raise MCPError(f"MCP server error {response.status_code}: {response.text}")

            # Raise for other HTTP errors
            response.raise_for_status()

            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"MCP request timeout: {url}")
            raise MCPTimeoutError(f"Request to {endpoint} timed out after {self.timeout}s") from e

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to MCP server: {url}")
            raise MCPConnectionError(f"Cannot connect to MCP server at {self.server_url}") from e

        except (MCPNotFoundError, MCPValidationError, MCPError):
            # Re-raise our custom exceptions
            raise

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from MCP server: {e}")
            raise MCPError(f"MCP server error: {e}") from e

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile from Sanity.io via MCP.

        Args:
            user_id: User ID to fetch

        Returns:
            User profile if found, None if user doesn't exist

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPError: For other server errors
        """
        try:
            response = self._make_request('GET', f'/profiles/{user_id}')
            return response.json()

        except MCPNotFoundError:
            logger.info(f"User profile not found: {user_id}")
            return None

    def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Update user profile in Sanity.io via MCP.

        Args:
            user_id: User ID to update
            data: Profile data to update (partial updates supported)

        Returns:
            True if update successful

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPNotFoundError: If user not found
            MCPValidationError: If update data is invalid
            MCPError: For other server errors
        """
        response = self._make_request('PATCH', f'/profiles/{user_id}', json_data=data)
        return response.status_code == 200

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """
        Get conversation history from Redis cache.

        Args:
            conversation_id: Conversation ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages (empty list if conversation not found)

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPValidationError: If limit is invalid
            MCPError: For other server errors
        """
        try:
            response = self._make_request(
                'GET',
                f'/conversations/{conversation_id}',
                params={'limit': limit}
            )
            data = response.json()
            return data.get('messages', [])

        except MCPNotFoundError:
            logger.info(f"Conversation not found: {conversation_id}")
            return []

    def save_conversation_message(
        self,
        conversation_id: str,
        sender: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save a message to conversation history in Redis.

        Args:
            conversation_id: Conversation ID
            sender: Message sender ID
            message: Message content
            metadata: Optional message metadata

        Returns:
            True if message saved successfully

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPValidationError: If message data is invalid
            MCPError: For other server errors
        """
        response = self._make_request(
            'POST',
            f'/conversations/{conversation_id}/messages',
            json_data={
                'sender': sender,
                'message': message,
                'metadata': metadata or {}
            }
        )
        return response.status_code == 201

    def get_user_preferences(self, user_id: str) -> UserPreferences:
        """
        Get user preferences from SQLite via MCP.

        Args:
            user_id: User ID

        Returns:
            User preferences (returns defaults if not found)

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPError: For other server errors
        """
        try:
            response = self._make_request('GET', f'/preferences/{user_id}')
            return response.json()

        except MCPNotFoundError:
            logger.info(f"User preferences not found, using defaults: {user_id}")
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

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update user preferences in SQLite via MCP.

        Args:
            user_id: User ID
            preferences: Preferences to update (partial updates supported)

        Returns:
            True if update successful

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPValidationError: If preferences data is invalid
            MCPError: For other server errors
        """
        response = self._make_request(
            'PATCH',
            f'/preferences/{user_id}',
            json_data=preferences
        )
        return response.status_code == 200

    def get_message_templates(self, template_type: str = 'introduction') -> List[MessageTemplate]:
        """
        Get message templates from Sanity.io via MCP.

        Args:
            template_type: Type of template (introduction, follow_up, meeting_request, etc.)

        Returns:
            List of templates (empty list if none found)

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPError: For other server errors
        """
        try:
            response = self._make_request(
                'GET',
                '/templates',
                params={'type': template_type}
            )
            data = response.json()
            return data.get('templates', [])

        except MCPNotFoundError:
            logger.info(f"No templates found for type: {template_type}")
            return []

    def log_interaction(
        self,
        user_id: str,
        other_user_id: str,
        interaction_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log an interaction between users.

        Args:
            user_id: Primary user ID
            other_user_id: Other user ID
            interaction_type: Type of interaction (message, meeting, permission_*, etc.)
            metadata: Optional interaction metadata

        Returns:
            True if interaction logged successfully

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPValidationError: If interaction data is invalid
            MCPError: For other server errors
        """
        response = self._make_request(
            'POST',
            '/interactions',
            json_data={
                'user_id': user_id,
                'other_user_id': other_user_id,
                'interaction_type': interaction_type,
                'metadata': metadata or {}
            }
        )
        return response.status_code == 201

    def cache_get(self, key: str) -> Optional[Any]:
        """
        Get value from Redis cache.

        Args:
            key: Cache key

        Returns:
            Cached value if exists, None if not found

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPError: For other server errors
        """
        try:
            response = self._make_request('GET', f'/cache/{key}')
            data = response.json()
            return data.get('value')

        except MCPNotFoundError:
            return None

    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Optional time-to-live in seconds

        Returns:
            True if value cached successfully

        Raises:
            MCPConnectionError: If cannot connect to MCP server
            MCPTimeoutError: If request times out
            MCPValidationError: If value is not JSON-serializable
            MCPError: For other server errors
        """
        response = self._make_request(
            'POST',
            f'/cache/{key}',
            json_data={'value': value, 'ttl': ttl}
        )
        return response.status_code == 201

    def health_check(self) -> bool:
        """
        Check if MCP server is healthy and accessible.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = self._make_request('GET', '/health')
            data = response.json()
            return data.get('status') == 'healthy'

        except (MCPConnectionError, MCPTimeoutError, MCPError):
            logger.warning("MCP server health check failed")
            return False
