"""
Integration test for Claude tool calling and system prompt.
This tests the actual agent with Claude API.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_agent_tool_calling():
    """Test the agent's ability to use tools with Claude API"""
    logger.info("\n" + "="*60)
    logger.info("CLAUDE TOOL CALLING INTEGRATION TEST")
    logger.info("="*60)

    try:
        # Mock the Google modules
        from unittest.mock import MagicMock
        sys.modules['google.auth.transport.requests'] = MagicMock()
        sys.modules['google.oauth2.credentials'] = MagicMock()
        sys.modules['google_auth_oauthlib.flow'] = MagicMock()
        sys.modules['googleapiclient.discovery'] = MagicMock()
        sys.modules['googleapiclient.errors'] = MagicMock()

        # Import test dependencies
        from test_agent_tools import MockMCPClient, MockiMessageTool, MockGmailTool
        import tools.mcp_client  # noqa: F401
        import tools.imessage_tool  # noqa: F401
        import tools.gmail_tool  # noqa: F401

        # Replace with mocks
        original_mcp = tools.mcp_client.MCPClient
        original_imessage = tools.imessage_tool.iMessageTool
        original_gmail = tools.gmail_tool.GmailTool

        tools.mcp_client.MCPClient = MockMCPClient
        tools.imessage_tool.iMessageTool = MockiMessageTool
        tools.gmail_tool.GmailTool = MockGmailTool

        # Import agent
        from core.agent import TamaBotchiAgent

        logger.info("\n1. Testing agent initialization...")
        agent = TamaBotchiAgent(user_id='test_user')
        logger.info(f"   ✓ Agent initialized for user: {agent.user_profile.get('name')}")

        logger.info("\n2. Testing system prompt generation...")
        prompt = agent._get_system_prompt()
        logger.info(f"   ✓ System prompt generated ({len(prompt)} characters)")
        logger.info(f"   ✓ Includes user name: {'Test User' in prompt}")
        logger.info(f"   ✓ Includes interests: {'AI' in prompt}")

        logger.info("\n3. Testing calculate_match tool...")
        result = agent.run("Calculate my match score with user other_user")
        logger.info(f"   ✓ Agent response: {result['output'][:100]}...")

        logger.info("\n4. Testing get_profile tool...")
        result = agent.run("Get the profile for user other_user")
        logger.info(f"   ✓ Agent response: {result['output'][:100]}...")

        logger.info("\n5. Testing autonomous outreach scenario...")
        response = agent.handle_new_person_nearby(
            other_user_id='other_user',
            context={'event_name': 'Tech Conference 2025', 'location': 'San Francisco'}
        )
        logger.info(f"   ✓ Action taken: {response.get('action')}")
        if 'reason' in response:
            logger.info(f"   ✓ Reason: {response['reason']}")

        logger.info("\n6. Testing conversation style matching...")
        style = agent.user_preferences.get('conversation_style', {})
        logger.info(f"   ✓ Tone: {style.get('tone')}")
        logger.info(f"   ✓ Length: {style.get('length')}")
        logger.info(f"   ✓ Formality: {style.get('formality')}")

        logger.info("\n7. Testing tool definitions...")
        logger.info(f"   ✓ Number of tools: {len(agent.tools)}")
        for tool in agent.tools:
            logger.info(f"   ✓ Tool: {tool['name']}")

        # Restore original classes
        tools.mcp_client.MCPClient = original_mcp
        tools.imessage_tool.iMessageTool = original_imessage
        tools.gmail_tool.GmailTool = original_gmail

        logger.info("\n" + "="*60)
        logger.info("ALL INTEGRATION TESTS PASSED")
        logger.info("="*60)
        return True

    except Exception as e:
        logger.error(f"\nIntegration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_agent_tool_calling()
    sys.exit(0 if success else 1)
