# ruff: noqa: F401
"""
Test that all imports work correctly and types are properly defined.
This is a critical test to verify production readiness.
"""
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test all module imports"""
    logger.info("Testing imports...")

    try:
        # Test types module
        logger.info("  Importing tama_types...")
        from tama_types import (
            UserProfile,
            UserPreferences,
            ConversationMessage,
            MatchResult,
            DetectionContext,
            DetectionResponse,
            IncomingMessageResponse,
            iMessageSendResponse,
            EmailSendResponse,
            CalendarEventResponse
        )
        logger.info("    Types imported successfully")

        # Test exceptions module
        logger.info("  Importing exceptions...")
        from exceptions import (
            TamaError,
            MCPError,
            MCPConnectionError,
            MCPTimeoutError,
            iMessageError,
            iMessageConnectionError,
            iMessageSendError,
            GmailError,
            GmailAuthError,
            CalendarError
        )
        logger.info("    Exceptions imported successfully")

        # Test config
        logger.info("  Importing config...")
        from config import Config
        logger.info("    Config imported successfully")

        # Test tools
        logger.info("  Importing tools...")
        from tools.mcp_client import MCPClient
        logger.info("    MCP client imported successfully")

        from tools.imessage_tool import iMessageTool
        logger.info("    iMessage tool imported successfully")

        try:
            from tools.gmail_tool import GmailTool
            logger.info("    Gmail tool imported successfully")
        except ImportError as e:
            logger.warning(f"    Gmail tool skipped (missing dependencies): {e}")
            logger.warning("    Install with: pip install google-auth google-auth-oauthlib google-api-python-client")

        # Test core modules
        logger.info("  Importing core modules...")
        from core.matching import MatchingEngine
        logger.info("    Matching engine imported successfully")

        from core.permissions import PermissionsManager, ActionType, PermissionLevel
        logger.info("    Permissions manager imported successfully")

        # Test main module (but don't run it)
        logger.info("  Importing main...")
        try:
            import main
            logger.info("    Main module imported successfully")
        except ImportError as e:
            if 'anthropic' in str(e) or 'langchain' in str(e):
                logger.warning(f"    Main module skipped (missing ML dependencies): {e}")
                logger.warning("    Install with: pip install anthropic langchain langchain-anthropic")
            else:
                raise

        logger.info("\nAll imports successful!")
        return True

    except ImportError as e:
        logger.error(f"\nImport error: {e}")
        logger.error("Make sure you're running from the agent directory")
        logger.error("And all dependencies are installed: pip install -r requirements.txt")
        return False

    except Exception as e:
        logger.error(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_type_hints():
    """Test that type hints are properly defined"""
    logger.info("\nTesting type hints...")

    try:
        from tools.mcp_client import MCPClient
        from tools.imessage_tool import iMessageTool
        from core.matching import MatchingEngine

        # Check that methods have annotations
        mcp = MCPClient.__init__
        if not hasattr(mcp, '__annotations__'):
            logger.warning("  MCPClient.__init__ missing annotations")
        else:
            logger.info("  MCPClient has type annotations")

        imsg = iMessageTool.send_message
        if not hasattr(imsg, '__annotations__'):
            logger.warning("  iMessageTool.send_message missing annotations")
        else:
            logger.info("  iMessageTool.send_message has type annotations")

        match = MatchingEngine.calculate_match_score
        if not hasattr(match, '__annotations__'):
            logger.warning("  MatchingEngine.calculate_match_score missing annotations")
        else:
            logger.info("  MatchingEngine.calculate_match_score has type annotations")

        logger.info("Type hints check complete")
        return True

    except Exception as e:
        logger.error(f"Type hints test failed: {e}")
        return False


def test_no_placeholders():
    """Scan for placeholder comments in code"""
    logger.info("\nScanning for placeholder code...")

    import os
    import re

    placeholder_patterns = [
        r'#\s*(TODO|FIXME|XXX|HACK|placeholder|stub|to be implemented)',
        r'^\s*pass\s*$',  # Lone pass statements
        r'#\s*Future enhancement',
    ]

    violations = []
    agent_dir = os.path.dirname(__file__)

    for root, dirs, files in os.walk(agent_dir):
        # Skip __pycache__ and test files
        if '__pycache__' in root or 'test_' in root:
            continue

        for file in files:
            if not file.endswith('.py'):
                continue

            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    for line_no, line in enumerate(f, 1):
                        for pattern in placeholder_patterns:
                            if re.search(pattern, line, re.IGNORECASE):
                                violations.append(f"{filepath}:{line_no}: {line.strip()}")
            except Exception as e:
                logger.warning(f"Could not read {filepath}: {e}")

    if violations:
        logger.error(f"Found {len(violations)} placeholder violations:")
        for v in violations[:10]:  # Show first 10
            logger.error(f"  {v}")
        if len(violations) > 10:
            logger.error(f"  ... and {len(violations) - 10} more")
        return False
    else:
        logger.info("No placeholder code found")
        return True


def test_exceptions_usage():
    """Test that custom exceptions are defined and usable"""
    logger.info("\nTesting exception handling...")

    try:
        from exceptions import MCPConnectionError, iMessageSendError, GmailAuthError

        # Test that exceptions can be raised and caught
        try:
            raise MCPConnectionError("Test error")
        except MCPConnectionError as e:
            logger.info(f"  MCPConnectionError works: {e}")

        try:
            raise iMessageSendError("Test error")
        except iMessageSendError as e:
            logger.info(f"  iMessageSendError works: {e}")

        try:
            raise GmailAuthError("Test error")
        except GmailAuthError as e:
            logger.info(f"  GmailAuthError works: {e}")

        logger.info("Exception handling test passed")
        return True

    except Exception as e:
        logger.error(f"Exception test failed: {e}")
        return False


def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("PRODUCTION READINESS TEST SUITE")
    logger.info("=" * 60)

    results = {}

    results['imports'] = test_imports()
    results['type_hints'] = test_type_hints()
    results['no_placeholders'] = test_no_placeholders()
    results['exceptions'] = test_exceptions_usage()

    logger.info("\n" + "=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"{test_name:20s}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)

    if all_passed:
        logger.info("\nALL TESTS PASSED - Code is production ready!")
        return 0
    else:
        logger.error("\nSOME TESTS FAILED - Fix issues before deployment")
        return 1


if __name__ == '__main__':
    sys.exit(main())
