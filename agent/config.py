"""
Configuration management for TamaBotchi agent
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""

    # Anthropic
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-haiku-4-5-20251001')

    # iMessage Bridge
    IMESSAGE_SERVER_URL = os.getenv('IMESSAGE_SERVER_URL', 'http://localhost:5001')

    # MCP Server
    MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://localhost:5002')

    # Gmail API
    GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', './credentials/gmail_credentials.json')
    GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', './credentials/gmail_token.json')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    # Agent Settings
    AGENT_NAME = os.getenv('AGENT_NAME', 'TamaBotchi')
    HIGH_MATCH_THRESHOLD = float(os.getenv('HIGH_MATCH_THRESHOLD', 0.75))
    AUTO_SCHEDULE_ENABLED = os.getenv('AUTO_SCHEDULE_ENABLED', 'true').lower() == 'true'

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required")

        return True
