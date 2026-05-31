"""
iMessage Tool for sending messages via the bridge server.
"""
import requests
from typing import Optional, List
import logging

from config import Config
from tama_types import iMessageSendResponse, iMessageHistory
from exceptions import iMessageConnectionError, iMessageSendError

logger = logging.getLogger(__name__)


class iMessageTool:
    """Tool for sending iMessages via the macOS bridge server"""

    def __init__(self, server_url: Optional[str] = None, timeout: int = 10):
        """
        Initialize iMessage tool.

        Args:
            server_url: iMessage server URL, defaults to config value
            timeout: Request timeout in seconds

        Raises:
            iMessageConnectionError: If server URL not configured
        """
        self.server_url = server_url or Config.IMESSAGE_SERVER_URL
        self.timeout = timeout

        if not self.server_url:
            raise iMessageConnectionError("iMessage server URL not configured")

    def send_message(self, recipient: str, message: str) -> iMessageSendResponse:
        """
        Send an iMessage to a recipient.

        Args:
            recipient: Phone number or email of the recipient
            message: Message content to send

        Returns:
            Response dict with success status and details

        Raises:
            iMessageConnectionError: Cannot connect to iMessage server
            iMessageSendError: Failed to send message
        """
        try:
            response = requests.post(
                f"{self.server_url}/send",
                json={"recipient": recipient, "message": message},
                timeout=self.timeout
            )

            # Check for HTTP errors
            if response.status_code >= 500:
                raise iMessageSendError(
                    f"iMessage server error {response.status_code}: {response.text}"
                )

            if response.status_code == 400:
                raise iMessageSendError(
                    f"Invalid request: {response.text}"
                )

            response.raise_for_status()

            result: iMessageSendResponse = response.json()

            # Check if message actually sent successfully
            if not result.get('success', False):
                error_msg = result.get('error', 'Unknown error')
                raise iMessageSendError(f"Failed to send iMessage: {error_msg}")

            logger.info(f"Successfully sent iMessage to {recipient}")
            return result

        except requests.exceptions.Timeout as e:
            logger.error(f"iMessage server timeout: {self.server_url}")
            raise iMessageConnectionError(
                f"iMessage server timeout after {self.timeout}s"
            ) from e

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to iMessage server: {self.server_url}")
            raise iMessageConnectionError(
                f"Cannot connect to iMessage server at {self.server_url}"
            ) from e

        except (iMessageConnectionError, iMessageSendError):
            # Re-raise our custom exceptions
            raise

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from iMessage server: {e}")
            raise iMessageSendError(
                f"iMessage server HTTP error: {e}"
            ) from e

        except Exception as e:
            logger.error(f"Unexpected error sending iMessage: {e}")
            raise iMessageSendError(
                f"Unexpected error: {e}"
            ) from e

    def get_recent_messages(self, limit: int = 50) -> List[iMessageHistory]:
        """
        Get recent iMessages from the bridge server.

        Args:
            limit: Number of messages to retrieve (default 50, max 200)

        Returns:
            List of message dictionaries

        Raises:
            iMessageConnectionError: Cannot connect to iMessage server
            iMessageSendError: Server error retrieving messages
        """
        if limit > 200:
            limit = 200
            logger.warning("Message limit capped at 200")

        try:
            response = requests.get(
                f"{self.server_url}/messages",
                params={"limit": limit},
                timeout=self.timeout
            )

            response.raise_for_status()

            data = response.json()
            return data.get('messages', [])

        except requests.exceptions.Timeout as e:
            logger.error(f"iMessage server timeout: {self.server_url}")
            raise iMessageConnectionError(
                f"iMessage server timeout after {self.timeout}s"
            ) from e

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Cannot connect to iMessage server: {self.server_url}")
            raise iMessageConnectionError(
                f"Cannot connect to iMessage server at {self.server_url}"
            ) from e

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from iMessage server: {e}")
            raise iMessageSendError(
                f"Failed to retrieve messages: {e}"
            ) from e

    def health_check(self) -> bool:
        """
        Check if the iMessage bridge server is healthy.

        Returns:
            True if server is healthy and accessible, False otherwise
        """
        try:
            response = requests.get(
                f"{self.server_url}/health",
                timeout=5
            )

            if response.status_code != 200:
                logger.warning(f"iMessage server health check returned {response.status_code}")
                return False

            data = response.json()
            is_healthy = data.get('status') == 'healthy'

            if not is_healthy:
                logger.warning(f"iMessage server reports unhealthy status: {data}")

            return is_healthy

        except Exception as e:
            logger.warning(f"iMessage server health check failed: {e}")
            return False
