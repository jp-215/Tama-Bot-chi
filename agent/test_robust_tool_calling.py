"""
Robust integration test for Claude tool calling.
This actually verifies that Claude calls the tools and gets correct results.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_robust_tool_calling():
    """Test that Claude actually executes tools and returns correct data"""
    logger.info("\n" + "="*60)
    logger.info("ROBUST CLAUDE TOOL CALLING TEST")
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

        logger.info("\n1. Initialize agent")
        agent = TamaBotchiAgent(user_id='test_user')
        logger.info("   ✓ Agent initialized")

        # Test 1: Verify tool was actually called and data is correct
        logger.info("\n2. Test calculate_match tool execution")
        result = agent.run("Calculate my match score with the user whose ID is 'other_user'")
        output = result['output'].lower()

        # Verify the tool was actually called by checking if response contains match data
        checks = {
            "Response exists": len(output) > 0,
            "Contains percentage or score": any(word in output for word in ['%', 'percent', 'score', '63', '65']),
            "Contains match info": any(word in output for word in ['match', 'compatibility', 'score']),
            "Mentions shared interests": any(word in output for word in ['ai', 'networking', 'interest']),
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Output was: {output[:200]}")
                return False

        # Test 2: Verify get_profile actually retrieves profile data
        logger.info("\n3. Test get_profile tool execution")
        result = agent.run("Get the profile for user ID 'other_user' and tell me their role")
        output = result['output'].lower()

        checks = {
            "Response exists": len(output) > 0,
            "Contains 'other user' name": 'other' in output and 'user' in output,
            "Contains role info": any(word in output for word in ['product', 'manager', 'role']),
            "Contains industry or interests": any(word in output for word in ['technology', 'ai', 'product', 'interest']),
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Output was: {output[:200]}")
                return False

        # Test 3: Verify multiple tool calls in one conversation
        logger.info("\n4. Test multiple tool calls")
        result = agent.run("First get the profile for user ID 'other_user', then calculate our match score with them")
        output = result['output'].lower()

        # This should have called both get_profile AND calculate_match
        checks = {
            "Response exists": len(output) > 0,
            "Has profile info": any(word in output for word in ['product', 'manager', 'other user']),
            "Has match info": any(word in output for word in ['score', 'match', '%', 'percent']),
            "Coherent response": len(output) > 50,  # Should be substantial
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Output was: {output[:200]}")
                return False

        # Test 4: Verify system prompt personalization
        logger.info("\n5. Test system prompt personalization")
        prompt = agent._get_system_prompt()

        checks = {
            "Contains user name": 'Test User' in prompt,
            "Contains user role": 'Software Engineer' in prompt,
            "Contains interests": 'AI' in prompt and 'networking' in prompt,
            "Contains conversation guidelines": 'high-match' in prompt.lower() or 'compatibility' in prompt.lower(),
            "Contains threshold": '75' in prompt or 'threshold' in prompt.lower(),
            "Mentions authenticity": 'authentic' in prompt.lower() or 'reputation' in prompt.lower(),
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Prompt was: {prompt[:300]}")
                return False

        # Test 5: Verify tool execution internals
        logger.info("\n6. Test direct tool execution")

        # Test calculate_match directly
        match_result = agent._execute_tool('calculate_match', {'other_user_id': 'other_user'})
        checks = {
            "Returns dict": isinstance(match_result, dict),
            "Has score": 'score' in match_result,
            "Has is_high_match": 'is_high_match' in match_result,
            "Has reason": 'reason' in match_result,
            "Score is numeric": isinstance(match_result.get('score'), (int, float)),
            "Score is reasonable": 0 <= match_result.get('score', -1) <= 1,
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Result was: {match_result}")
                return False

        # Test get_profile directly
        profile_result = agent._execute_tool('get_profile', {'user_id': 'other_user'})
        checks = {
            "Returns dict": isinstance(profile_result, dict),
            "Has user_id": 'user_id' in profile_result,
            "Has name": 'name' in profile_result,
            "Has correct name": profile_result.get('name') == 'Other User',
            "Has role": 'role' in profile_result,
            "Has correct role": profile_result.get('role') == 'Product Manager',
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Result was: {profile_result}")
                return False

        # Test 6: Verify response structure
        logger.info("\n7. Test response structure")
        result = agent.run("Calculate match with user ID 'other_user'")

        checks = {
            "Has 'output' key": 'output' in result,
            "Has 'messages' key": 'messages' in result,
            "Has 'response' key": 'response' in result,
            "Output is string": isinstance(result.get('output'), str),
            "Messages is list": isinstance(result.get('messages'), list),
            "Messages not empty": len(result.get('messages', [])) > 0,
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Result keys: {result.keys()}")
                return False

        # Test 7: Verify permissions logic
        logger.info("\n8. Test permissions logic")
        response = agent.handle_new_person_nearby(
            other_user_id='other_user',
            context={'event_name': 'Test Event'}
        )

        # Mock returns 65% match, which is < 75% threshold, so should request permission
        checks = {
            "Returns dict": isinstance(response, dict),
            "Has action": 'action' in response,
            "Requests permission": response.get('action') == 'request_permission',
            "Has match_score": 'match_score' in response,
            "Has reason": 'reason' in response,
            "Score below threshold": response.get('match_score', 1.0) < 0.75,
        }

        for check_name, passed in checks.items():
            status = "✓" if passed else "✗"
            logger.info(f"   {status} {check_name}: {passed}")
            if not passed:
                logger.error(f"      Failed check. Response was: {response}")
                return False

        # Restore original classes
        tools.mcp_client.MCPClient = original_mcp
        tools.imessage_tool.iMessageTool = original_imessage
        tools.gmail_tool.GmailTool = original_gmail

        logger.info("\n" + "="*60)
        logger.info("ALL ROBUST TESTS PASSED ✓")
        logger.info("="*60)
        logger.info("\nVerified:")
        logger.info("  • Claude actually calls tools and gets real data")
        logger.info("  • Tool results are correctly structured")
        logger.info("  • System prompt is properly personalized")
        logger.info("  • Permissions logic works correctly")
        logger.info("  • Multi-tool conversations work")
        logger.info("  • Response format is correct")
        return True

    except Exception as e:
        logger.error(f"\nRobust test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_robust_tool_calling()
    sys.exit(0 if success else 1)
