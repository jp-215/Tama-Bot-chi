"""
TamaBotchi iMessage Watcher - Auto-Reply Daemon

Polls ~/Library/Messages/chat.db for new incoming iMessages,
routes them through the TamaBotchi Agent API (Claude), and sends
AI-generated responses back via AppleScript.

Usage:
    python watcher.py

Requires:
    - iMessage Server running on port 5001
    - Agent API running on port 5000
    - MCP Server running on port 5002
    - Full Disk Access granted to Terminal
"""
import sqlite3
import os
import time
import requests
import logging
import signal
import sys
from typing import Optional, Dict, List, Any

# Configuration
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://127.0.0.1:5000")
IMESSAGE_SERVER_URL = os.getenv("IMESSAGE_SERVER_URL", "http://127.0.0.1:5001")
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL", "3"))
USER_ID = os.getenv("TAMA_USER_ID", "default_user")
MESSAGES_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("tamabotchi-watcher")

# Track state
running = True
last_processed_rowid: int = 0
# Conversations keyed by sender handle (phone/email)
active_conversations: Dict[str, str] = {}
# Track messages we sent so we don't reply to ourselves
our_sent_messages: set = set()


def signal_handler(sig: int, frame: Any) -> None:
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutting down watcher...")
    running = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def get_latest_rowid() -> int:
    """
    Get the highest ROWID in the message table to use as our starting point.
    We only want to respond to messages that arrive AFTER the watcher starts.

    Returns:
        The latest ROWID in the messages database.

    Raises:
        sqlite3.OperationalError: If the database cannot be read.
    """
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(ROWID) FROM message")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result[0] else 0


def get_new_incoming_messages(since_rowid: int) -> List[Dict[str, Any]]:
    """
    Query chat.db for new incoming messages since a given ROWID.

    Args:
        since_rowid: Only return messages with ROWID greater than this.

    Returns:
        List of message dicts with keys: id, text, sender, date, chat_id

    Raises:
        sqlite3.OperationalError: If database is locked or inaccessible.
    """
    conn = sqlite3.connect(MESSAGES_DB)
    cursor = conn.cursor()

    query = """
        SELECT
            message.ROWID,
            message.text,
            message.date,
            message.is_from_me,
            handle.id as sender,
            chat.chat_identifier
        FROM message
        LEFT JOIN handle ON message.handle_id = handle.ROWID
        LEFT JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
        LEFT JOIN chat ON chat_message_join.chat_id = chat.ROWID
        WHERE message.ROWID > ?
          AND message.is_from_me = 0
          AND message.text IS NOT NULL
          AND message.text != ''
        ORDER BY message.ROWID ASC
    """

    cursor.execute(query, (since_rowid,))
    rows = cursor.fetchall()
    conn.close()

    messages = []
    for row in rows:
        mac_time = row[2] / 1000000000  # nanoseconds to seconds
        unix_time = mac_time + 978307200

        messages.append({
            "id": row[0],
            "text": row[1],
            "timestamp": unix_time,
            "sender": row[4],
            "chat_id": row[5],
        })

    return messages


def get_conversation_id(sender: str) -> str:
    """
    Get or create a conversation ID for a sender.

    Args:
        sender: Phone number or email of the sender.

    Returns:
        A conversation ID string.
    """
    if sender not in active_conversations:
        # Create a deterministic conversation ID from the sender handle
        clean_sender = sender.replace("+", "").replace(" ", "").replace("-", "")
        active_conversations[sender] = f"imsg_{USER_ID}_{clean_sender}"
    return active_conversations[sender]


def send_to_agent(sender: str, message_text: str, conversation_id: str) -> Optional[str]:
    """
    Send an incoming message to the TamaBotchi Agent API for AI processing.

    Args:
        sender: The sender's phone/email
        message_text: The message content
        conversation_id: The conversation thread ID

    Returns:
        The AI-generated response text, or None if the agent fails.
    """
    try:
        response = requests.post(
            f"{AGENT_API_URL}/users/{USER_ID}/messages/incoming",
            json={
                "user_id": USER_ID,
                "sender_id": sender,
                "message": message_text,
                "conversation_id": conversation_id,
            },
            timeout=30,
        )

        if response.status_code != 200:
            logger.error(
                "Agent API returned %d: %s", response.status_code, response.text
            )
            return None

        data = response.json()
        ai_response = data.get("response", "")

        if data.get("should_notify_user"):
            logger.info(
                "Agent suggests user should take over conversation with %s", sender
            )

        return ai_response

    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Agent API at %s", AGENT_API_URL)
        return None
    except requests.exceptions.Timeout:
        logger.error("Agent API request timed out")
        return None
    except Exception as e:
        logger.error("Unexpected error calling Agent API: %s", e)
        return None


def send_imessage_reply(recipient: str, message: str) -> bool:
    """
    Send a reply via the iMessage server.

    Args:
        recipient: Phone number or email to send to.
        message: Message content.

    Returns:
        True if the message was sent successfully.
    """
    try:
        response = requests.post(
            f"{IMESSAGE_SERVER_URL}/send",
            json={"recipient": recipient, "message": message},
            timeout=15,
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                our_sent_messages.add(message[:100])  # Track to avoid echo
                return True

        logger.error(
            "iMessage server returned %d: %s", response.status_code, response.text
        )
        return False

    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to iMessage server at %s", IMESSAGE_SERVER_URL)
        return False
    except Exception as e:
        logger.error("Error sending iMessage reply: %s", e)
        return False


def check_services() -> Dict[str, bool]:
    """
    Check if required services are running.

    Returns:
        Dict mapping service name to availability boolean.
    """
    services = {"agent": False, "imessage": False}

    try:
        r = requests.get(f"{AGENT_API_URL}/health", timeout=5)
        services["agent"] = r.status_code == 200
    except Exception:
        pass

    try:
        r = requests.get(f"{IMESSAGE_SERVER_URL}/health", timeout=5)
        services["imessage"] = r.status_code == 200
    except Exception:
        pass

    return services


def main() -> None:
    """
    Main polling loop. Watches chat.db for new incoming messages
    and routes them through the AI agent for auto-reply.
    """
    global last_processed_rowid

    print("=" * 60)
    print("  TamaBotchi iMessage Auto-Reply Watcher")
    print("=" * 60)
    print()

    # Check database access
    if not os.path.exists(MESSAGES_DB):
        logger.error("Messages database not found at %s", MESSAGES_DB)
        sys.exit(1)

    if not os.access(MESSAGES_DB, os.R_OK):
        logger.error("Cannot read Messages database - grant Full Disk Access")
        sys.exit(1)

    logger.info("Messages database: %s", MESSAGES_DB)

    # Check services
    services = check_services()
    logger.info("Agent API (%s): %s", AGENT_API_URL, "UP" if services["agent"] else "DOWN")
    logger.info(
        "iMessage Server (%s): %s",
        IMESSAGE_SERVER_URL,
        "UP" if services["imessage"] else "DOWN",
    )

    if not services["agent"]:
        logger.error("Agent API is not running. Start it first.")
        sys.exit(1)

    if not services["imessage"]:
        logger.error("iMessage Server is not running. Start it first.")
        sys.exit(1)

    # Start from the latest message (don't reply to old messages)
    last_processed_rowid = get_latest_rowid()
    logger.info(
        "Starting from message ROWID %d - will only respond to NEW messages",
        last_processed_rowid,
    )
    logger.info("Polling every %d seconds...", POLL_INTERVAL_SECONDS)
    logger.info("User ID: %s", USER_ID)
    print()
    logger.info("Waiting for incoming iMessages...")
    print()

    while running:
        try:
            new_messages = get_new_incoming_messages(last_processed_rowid)

            for msg in new_messages:
                sender = msg["sender"]
                text = msg["text"]
                msg_id = msg["id"]

                # Skip if this looks like something we sent (echo prevention)
                if text[:100] in our_sent_messages:
                    last_processed_rowid = msg_id
                    continue

                logger.info(
                    "New message from %s: %s",
                    sender,
                    text[:80] + ("..." if len(text) > 80 else ""),
                )

                # Get conversation ID for this sender
                conversation_id = get_conversation_id(sender)

                # Send to AI agent for response
                logger.info("Generating AI response...")
                ai_response = send_to_agent(sender, text, conversation_id)

                if ai_response:
                    # Send the response back via iMessage
                    logger.info(
                        "Sending reply: %s",
                        ai_response[:80] + ("..." if len(ai_response) > 80 else ""),
                    )
                    success = send_imessage_reply(sender, ai_response)

                    if success:
                        logger.info("Reply sent successfully to %s", sender)
                    else:
                        logger.error("Failed to send reply to %s", sender)
                else:
                    logger.warning("No response from agent for message from %s", sender)

                # Update the watermark regardless of success
                last_processed_rowid = msg_id

            time.sleep(POLL_INTERVAL_SECONDS)

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e):
                logger.warning("Database is locked, retrying in %ds...", POLL_INTERVAL_SECONDS)
                time.sleep(POLL_INTERVAL_SECONDS)
            else:
                logger.error("Database error: %s", e)
                time.sleep(POLL_INTERVAL_SECONDS)

        except Exception as e:
            logger.error("Unexpected error in poll loop: %s", e)
            time.sleep(POLL_INTERVAL_SECONDS)

    logger.info("Watcher stopped.")


if __name__ == "__main__":
    main()
