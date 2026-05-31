"""
TamaBotchi iMessage Bridge Server
Runs on macOS to send/receive iMessages via AppleScript
"""
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import datetime
import sqlite3
from threading import Lock
from typing import Optional


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup, regardless of how uvicorn launches the app."""
    init_db()
    yield


app = FastAPI(title="TamaBotchi iMessage Bridge", version="1.0.0", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database for tracking sent messages
DB_PATH = os.path.join(os.path.dirname(__file__), 'imessage_log.db')
db_lock = Lock()


def init_db():
    """Initialize the message log database"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent',
                error TEXT
            )
        ''')
        conn.commit()


def _escape_applescript_string(text: str) -> str:
    """
    Escape a string for safe embedding in an AppleScript double-quoted string.

    Backslashes must be escaped first, then double quotes, then newlines
    are converted to AppleScript's return character concatenation syntax.

    Args:
        text: Raw string to escape

    Returns:
        Escaped string safe to embed between AppleScript double quotes
    """
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\n', '" & return & "')
    return text


def send_imessage(phone_number: str, message: str) -> dict:
    """
    Send an iMessage using AppleScript

    Args:
        phone_number: Recipient's phone number or email
        message: Message content to send

    Returns:
        dict with status and any error information
    """
    escaped_message = _escape_applescript_string(message)
    escaped_phone = phone_number.replace('"', '\\"')

    applescript = f'''tell application "Messages"
    set targetService to 1st account whose service type = iMessage
    set targetBuddy to participant "{escaped_phone}" of targetService
    send "{escaped_message}" to targetBuddy
end tell'''

    try:
        result = subprocess.run(
            ['osascript', '-e', applescript],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            # Log successful send
            with db_lock:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        'INSERT INTO messages (recipient, message, status) VALUES (?, ?, ?)',
                        (phone_number, message, 'sent')
                    )
                    conn.commit()

            return {
                'success': True,
                'recipient': phone_number,
                'message': message,
                'sent_at': datetime.now().isoformat()
            }
        else:
            error_msg = result.stderr or 'Unknown error'

            # Log failed send
            with db_lock:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        'INSERT INTO messages (recipient, message, status, error) VALUES (?, ?, ?, ?)',
                        (phone_number, message, 'failed', error_msg)
                    )
                    conn.commit()

            return {
                'success': False,
                'error': error_msg
            }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'AppleScript execution timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_recent_messages(chat_id: str = None, limit: int = 50) -> list:
    """
    Read recent iMessages from the Messages database

    Args:
        chat_id: Optional specific chat to filter by
        limit: Number of recent messages to retrieve

    Returns:
        List of message dictionaries
    """
    # macOS stores iMessages in ~/Library/Messages/chat.db
    messages_db = os.path.expanduser('~/Library/Messages/chat.db')

    if not os.path.exists(messages_db):
        return {'error': 'Messages database not found'}

    try:
        conn = sqlite3.connect(messages_db)
        cursor = conn.cursor()

        # Query to get recent messages
        # Note: date is in Mac absolute time (seconds since 2001-01-01)
        query = '''
            SELECT
                message.ROWID,
                message.text,
                message.date,
                message.is_from_me,
                handle.id as sender
            FROM message
            LEFT JOIN handle ON message.handle_id = handle.ROWID
            ORDER BY message.date DESC
            LIMIT ?
        '''

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        messages = []
        for row in rows:
            # Convert Mac absolute time to Unix timestamp
            mac_time = row[2] / 1000000000  # nanoseconds to seconds
            unix_time = mac_time + 978307200  # Seconds between 1970 and 2001

            messages.append({
                'id': row[0],
                'text': row[1],
                'timestamp': unix_time,
                'is_from_me': bool(row[3]),
                'sender': row[4]
            })

        conn.close()
        return messages

    except Exception as e:
        return {'error': str(e)}


# Pydantic models
class SendMessageRequest(BaseModel):
    recipient: str
    message: str


class MessageResponse(BaseModel):
    success: bool
    recipient: Optional[str] = None
    message: Optional[str] = None
    sent_at: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


@app.get('/health', response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status='healthy',
        service='imessage-bridge',
        timestamp=datetime.now().isoformat()
    )


@app.post('/send', response_model=MessageResponse)
async def send_message(request: SendMessageRequest):
    """
    Send an iMessage

    Request body:
    {
        "recipient": "+1234567890",
        "message": "Hello from TamaBotchi!"
    }
    """
    result = send_imessage(request.recipient, request.message)

    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to send message'))

    return MessageResponse(**result)


@app.get('/messages')
async def get_messages(limit: int = 50, chat_id: Optional[str] = None):
    """
    Get recent iMessages

    Query params:
    - limit: number of messages to retrieve (default 50)
    - chat_id: optional specific chat ID
    """
    messages = get_recent_messages(chat_id, limit)

    return {
        'messages': messages,
        'count': len(messages) if isinstance(messages, list) else 0
    }


@app.get('/logs')
async def get_logs(limit: int = 100):
    """Get message send logs from our database"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM messages ORDER BY sent_at DESC LIMIT ?',
            (limit,)
        )

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        logs = [dict(zip(columns, row)) for row in rows]

    return {
        'logs': logs,
        'count': len(logs)
    }


if __name__ == '__main__':
    import uvicorn

    # Run server (lifespan handles init_db)
    print("🚀 TamaBotchi iMessage Bridge Server starting...")
    print("📱 Make sure you have granted Full Disk Access to Terminal/iTerm")
    print("⚙️  System Preferences > Security & Privacy > Privacy > Full Disk Access")
    print("")

    uvicorn.run(app, host='0.0.0.0', port=5001)
