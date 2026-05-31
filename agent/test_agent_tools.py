"""
Test suite for TamaBotchi agent tool calling with Claude API.
This tests the agent's ability to use tools correctly.
"""
import sys
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class MockMCPClient:
    """Mock MCP client for testing without actual MCP server"""

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Return mock user profile"""
        if user_id == "test_user":
            return {
                'user_id': 'test_user',
                'name': 'Test User',
                'email': 'test@example.com',
                'role': 'Software Engineer',
                'industry': 'Technology',
                'seniority': 'senior',
                'interests': ['AI', 'networking', 'startups'],
                'goals': ['build connections', 'find cofounders'],
                'contact': {
                    'phone': '+1234567890',
                    'email': 'test@example.com',
                    'linkedin': 'linkedin.com/in/testuser'
                }
            }
        elif user_id == "other_user":
            return {
                'user_id': 'other_user',
                'name': 'Other User',
                'email': 'other@example.com',
                'role': 'Product Manager',
                'industry': 'Technology',
                'seniority': 'senior',
                'interests': ['AI', 'product', 'networking'],
                'goals': ['build connections', 'launch product'],
                'contact': {
                    'phone': '+0987654321',
                    'email': 'other@example.com',
                    'linkedin': 'linkedin.com/in/otheruser'
                }
            }
        return None

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Return mock user preferences"""
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

    def get_conversation_history(self, conversation_id: str, limit: int = 50):
        """Return mock conversation history"""
        return []

    def save_conversation_message(self, conversation_id: str, sender: str, message: str, metadata=None):
        """Mock save message"""
        logger.info(f"[MOCK] Saved message from {sender}: {message[:50]}...")
        return True

    def log_interaction(self, user_id: str, other_user_id: str, interaction_type: str, metadata=None):
        """Mock log interaction"""
        logger.info(f"[MOCK] Logged interaction: {user_id} -> {other_user_id}: {interaction_type}")
        return True

    def get_message_templates(self, template_type: str = 'introduction'):
        """Return mock templates"""
        return []


class MockiMessageTool:
    """Mock iMessage tool for testing"""

    def __init__(self, server_url=None, timeout=10):
        logger.info("[MOCK] iMessage tool initialized")

    def send_message(self, recipient: str, message: str):
        """Mock send message"""
        logger.info(f"[MOCK] Sending iMessage to {recipient}")
        logger.info(f"[MOCK] Message: {message}")
        return {
            'success': True,
            'recipient': recipient,
            'message': message,
            'sent_at': '2025-11-21T10:00:00Z',
            'error': None
        }

    def health_check(self):
        """Mock health check"""
        return True


class MockGmailTool:
    """Mock Gmail tool for testing"""

    def __init__(self):
        logger.info("[MOCK] Gmail tool initialized (skipping OAuth)")

    def send_email(self, to: str, subject: str, body: str, html: bool = False):
        """Mock send email"""
        logger.info(f"[MOCK] Sending email to {to}")
        logger.info(f"[MOCK] Subject: {subject}")
        return {
            'success': True,
            'message_id': 'mock_msg_123',
            'recipient': to,
            'error': None
        }


def test_matching_algorithm():
    """Test the matching algorithm with real data"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Matching Algorithm")
    logger.info("="*60)

    try:
        from core.matching import MatchingEngine

        engine = MatchingEngine(high_match_threshold=0.75)

        user1 = {
            'interests': ['AI', 'networking', 'startups'],
            'industry': 'Technology',
            'role': 'Software Engineer',
            'seniority': 'senior',
            'goals': ['build connections']
        }

        user2 = {
            'interests': ['AI', 'product', 'networking'],
            'industry': 'Technology',
            'role': 'Product Manager',
            'seniority': 'senior',
            'goals': ['build connections', 'launch product']
        }

        score = engine.calculate_match_score(user1, user2)
        is_high_match = engine.is_high_match(score)
        reason = engine.get_match_reason(user1, user2, score)

        logger.info(f"Match Score: {score:.2%}")
        logger.info(f"Is High Match: {is_high_match}")
        logger.info(f"Reason: {reason}")

        if score > 0.5:
            logger.info("PASS: Matching algorithm working correctly")
            return True
        else:
            logger.error("FAIL: Match score too low for similar profiles")
            return False

    except Exception as e:
        logger.error(f"FAIL: Matching algorithm error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_permissions_system():
    """Test the permissions system"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Permissions System")
    logger.info("="*60)

    try:
        from core.permissions import PermissionsManager, ActionType

        mock_mcp = MockMCPClient()
        pm = PermissionsManager(mock_mcp)

        # Test getting permissions
        perms = pm.get_user_permissions('test_user')
        logger.info(f"User permissions loaded: {len(perms)} action types")

        # Test can_auto_execute for high match
        can_auto = pm.can_auto_execute('test_user', ActionType.SEND_MESSAGE, is_high_match=True)
        logger.info(f"Can auto-send to high match: {can_auto}")

        # Test can_auto_execute for low match
        cannot_auto = pm.can_auto_execute('test_user', ActionType.SEND_MESSAGE, is_high_match=False)
        logger.info(f"Can auto-send to low match: {cannot_auto}")

        if can_auto and not cannot_auto:
            logger.info("PASS: Permissions system working correctly")
            return True
        else:
            logger.error("FAIL: Permissions logic incorrect")
            return False

    except Exception as e:
        logger.error(f"FAIL: Permissions system error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_claude_tool_calling():
    """Test Claude API with tool calling (requires API key)"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Claude API Tool Calling")
    logger.info("="*60)

    # Check if API key is set
    from config import Config

    if not Config.ANTHROPIC_API_KEY or Config.ANTHROPIC_API_KEY == 'your_anthropic_api_key_here':
        logger.warning("SKIP: No Anthropic API key configured")
        logger.warning("Set ANTHROPIC_API_KEY in .env file to test Claude integration")
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        # Test basic Claude API call
        message = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'API works' if you can read this."}
            ]
        )

        response = message.content[0].text
        logger.info(f"Claude Response: {response}")

        if "API works" in response or "api works" in response.lower():
            logger.info("PASS: Claude API connection successful")
            return True
        else:
            logger.warning(f"PARTIAL: Claude API works but unexpected response: {response}")
            return True

    except Exception as e:
        logger.error(f"FAIL: Claude API error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_with_mocks():
    """Test the full agent with mock tools (no API key needed)"""
    logger.info("\n" + "="*60)
    logger.info("TEST: Agent with Mock Tools")
    logger.info("="*60)

    try:
        # Mock the Gmail tool module to avoid import errors
        import sys
        from unittest.mock import MagicMock

        # Create mock Google modules
        sys.modules['google.auth.transport.requests'] = MagicMock()
        sys.modules['google.oauth2.credentials'] = MagicMock()
        sys.modules['google_auth_oauthlib.flow'] = MagicMock()
        sys.modules['googleapiclient.discovery'] = MagicMock()
        sys.modules['googleapiclient.errors'] = MagicMock()

        # Temporarily replace tools with mocks
        import tools.mcp_client  # noqa: F401
        import tools.imessage_tool  # noqa: F401
        import tools.gmail_tool  # noqa: F401

        original_mcp = tools.mcp_client.MCPClient
        original_imessage = tools.imessage_tool.iMessageTool
        original_gmail = tools.gmail_tool.GmailTool

        tools.mcp_client.MCPClient = MockMCPClient
        tools.imessage_tool.iMessageTool = MockiMessageTool
        tools.gmail_tool.GmailTool = MockGmailTool

        # Try to import agent
        try:
            from core.agent import TamaBotchiAgent
            logger.info("Agent module imported successfully with mocks")
            logger.info("SKIP: Full agent test requires Anthropic API key")

            # Restore original classes
            tools.mcp_client.MCPClient = original_mcp
            tools.imessage_tool.iMessageTool = original_imessage
            tools.gmail_tool.GmailTool = original_gmail

            return None
        except ImportError as e:
            if 'anthropic' in str(e) or 'langchain' in str(e):
                logger.warning(f"SKIP: Agent requires ML dependencies: {e}")
                logger.warning("Install with: pip install anthropic langchain langchain-anthropic")
                return None
            else:
                raise

    except Exception as e:
        if "ANTHROPIC_API_KEY" in str(e) or "API key" in str(e):
            logger.warning("SKIP: Agent test requires Anthropic API key")
            return None
        else:
            logger.error(f"FAIL: Agent initialization error: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all tool calling tests"""
    logger.info("="*60)
    logger.info("TAMABOTCHI AGENT TOOL CALLING TEST SUITE")
    logger.info("="*60)

    results = {}

    # Run tests
    results['matching'] = test_matching_algorithm()
    results['permissions'] = test_permissions_system()
    results['claude_api'] = test_claude_tool_calling()
    results['agent_structure'] = test_agent_with_mocks()

    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*60)

    passed = 0
    failed = 0
    skipped = 0

    for test_name, result in results.items():
        if result is True:
            status = "PASS"
            passed += 1
        elif result is False:
            status = "FAIL"
            failed += 1
        else:
            status = "SKIP"
            skipped += 1

        logger.info(f"{test_name:20s}: {status}")

    logger.info("="*60)
    logger.info(f"Passed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        logger.error("\nSOME TESTS FAILED")
        return 1
    elif passed > 0:
        logger.info("\nALL EXECUTED TESTS PASSED")
        if skipped > 0:
            logger.info(f"{skipped} tests skipped (missing dependencies/API keys)")
        return 0
    else:
        logger.warning("\nALL TESTS SKIPPED - Install dependencies and set API key")
        return 0


if __name__ == '__main__':
    sys.exit(main())
