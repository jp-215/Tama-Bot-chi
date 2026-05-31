"""
Core TamaBotchi AI Agent with Claude + LangChain
"""
import anthropic
from anthropic import Anthropic
from typing import Dict, List, Optional
import json
import logging

from config import Config
from tools.imessage_tool import iMessageTool
from tools.mcp_client import MCPClient
from core.matching import MatchingEngine
from core.permissions import PermissionsManager, ActionType

logger = logging.getLogger(__name__)


class TamaBotchiAgent:
    """Main AI agent for TamaBotchi networking"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.anthropic = Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        # Initialize tools
        self.imessage_tool = iMessageTool()
        self.mcp_client = MCPClient()

        # Initialize core systems
        self.matching_engine = MatchingEngine(Config.HIGH_MATCH_THRESHOLD)
        self.permissions_manager = PermissionsManager(self.mcp_client)

        # Get user profile and preferences - MCP may not be running, fall back to empty defaults
        try:
            self.user_profile = self.mcp_client.get_user_profile(user_id) or {}
        except Exception as e:
            logger.warning("MCP unavailable, user profile not loaded: %s", e)
            self.user_profile = {}

        try:
            self.user_preferences = self.mcp_client.get_user_preferences(user_id)
        except Exception as e:
            logger.warning("MCP unavailable, user preferences not loaded: %s", e)
            self.user_preferences = {
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

        # Initialize LangChain agent
        self._setup_langchain_agent()

    def _setup_langchain_agent(self) -> None:
        """No tools configured - this is a pure iMessage agent."""
        self.tools: List[Dict] = []

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        user_name = self.user_profile.get('name', 'User')
        user_role = self.user_profile.get('role', 'professional')
        user_interests = ', '.join(self.user_profile.get('interests', []))
        conversation_style = self.user_preferences.get('conversation_style', {})

        return f"""You are TamaBotchi, an AI networking assistant for {user_name}.

Your primary role is to help {user_name} connect with interesting people at events and build meaningful professional relationships.

About {user_name}:
- Role: {user_role}
- Interests: {user_interests}
- Communication style: {json.dumps(conversation_style)}

Your capabilities:
1. Send iMessages and emails on {user_name}'s behalf
2. Schedule calendar meetings
3. Calculate compatibility with potential connections
4. Adapt conversation style based on the person you're talking to

Guidelines:
- Be friendly, professional, and authentic
- Match {user_name}'s communication style (tone, length, formality)
- When reaching out, mention why you think there's a good connection
- Always prioritize building genuine relationships over forced networking
- For high-match people (compatibility > 75%), you can autonomously reach out
- For lower matches, describe why you want to connect and ask for approval first
- Learn from responses and adapt your approach

When someone responds:
1. Analyze their response tone and style
2. Find common ground or interesting topics
3. Keep the conversation flowing naturally
4. Look for opportunities to suggest meeting in person
5. Ask if {user_name} wants to take over the conversation when appropriate

Remember: You represent {user_name}, so maintain their reputation and authenticity."""

    def handle_new_person_nearby(self, other_user_id: str, context: Dict) -> Dict:
        """
        Handle when a new person is detected nearby

        Args:
            other_user_id: ID of the person detected
            context: Context about the detection (event, location, etc.)

        Returns:
            dict with action taken and details
        """
        # Get their profile
        other_profile = self.mcp_client.get_user_profile(other_user_id)

        if not other_profile:
            return {'action': 'skip', 'reason': 'No profile found'}

        # Calculate match score
        match_score = self.matching_engine.calculate_match_score(
            self.user_profile,
            other_profile
        )

        is_high_match = self.matching_engine.is_high_match(match_score)

        # Check permissions
        can_auto_message = self.permissions_manager.can_auto_execute(
            self.user_id,
            ActionType.SEND_MESSAGE,
            is_high_match
        )

        if can_auto_message:
            # Autonomously reach out
            return self._autonomous_outreach(other_user_id, other_profile, match_score, context)
        else:
            # Ask user for permission
            return {
                'action': 'request_permission',
                'other_user': other_profile,
                'match_score': match_score,
                'reason': self.matching_engine.get_match_reason(
                    self.user_profile,
                    other_profile,
                    match_score
                ),
                'context': context
            }

    def _autonomous_outreach(
        self,
        other_user_id: str,
        other_profile: Dict,
        match_score: float,
        context: Dict
    ) -> Dict:
        """Autonomously reach out to a high-match person"""

        # Craft personalized message using Claude
        match_reason = self.matching_engine.get_match_reason(
            self.user_profile,
            other_profile,
            match_score
        )

        prompt = f"""You're reaching out to {other_profile.get('name')} on behalf of {self.user_profile.get('name')}.

Context:
- You're both at: {context.get('event_name', 'the same event')}
- Match reason: {match_reason}
- Match score: {match_score:.0%}

{other_profile.get('name')}'s profile:
{json.dumps(other_profile, indent=2)}

Craft a brief, friendly iMessage introduction (2-3 sentences max). Be authentic and mention the specific connection point."""

        response = self.run(prompt)
        message = response.get('output', '')

        phone = other_profile.get('contact', {}).get('phone')

        if phone:
            send_result = self.imessage_tool.send_message(phone, message)
            result = {
                'action': 'sent_imessage',
                'recipient': other_profile.get('name'),
                'message': message,
                'success': send_result.get('success', False)
            }
        else:
            result = {
                'action': 'no_contact_method',
                'recipient': other_profile.get('name')
            }

        # Log the interaction
        self.mcp_client.log_interaction(
            self.user_id,
            other_user_id,
            'autonomous_outreach',
            {'match_score': match_score, 'context': context}
        )

        return result

    def handle_incoming_message(
        self,
        sender_id: str,
        message: str,
        conversation_id: str
    ) -> Dict:
        """
        Handle an incoming message from someone

        Args:
            sender_id: ID of the sender
            message: Message content
            conversation_id: Conversation ID

        Returns:
            dict with response and actions
        """
        history: List[Dict] = []
        sender_profile: Dict = {}

        # Ask Claude to write the reply - output must be plain text only (sent directly as iMessage)
        history_text = json.dumps(history[-5:], indent=2) if history else 'No prior history'
        prompt = f"""You are replying to an iMessage from {sender_profile.get('name', 'someone')}.

Their message: "{message}"

Conversation history:
{history_text}

Write your reply. Output the reply text only - no analysis, no headers, no bullet points, no markdown. Just the plain message text you would send back."""

        response = self.run(prompt)

        output = response.get('output', '')

        return {
            'response': output,
            'should_notify_user': 'take over' in output.lower(),
            'conversation_id': conversation_id
        }

    def run(self, task: str, chat_history: Optional[List[Dict]] = None) -> Dict:
        """
        Run the agent with a specific task using Claude's tool calling

        Args:
            task: Task description
            chat_history: Optional conversation history

        Returns:
            dict with results
        """
        messages = []

        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)

        # Add user message
        messages.append({
            "role": "user",
            "content": task
        })

        # Call Claude - only pass tools if any are configured (API rejects empty list)
        create_kwargs: Dict = {
            "model": Config.CLAUDE_MODEL,
            "max_tokens": 4096,
            "system": self._get_system_prompt(),
            "messages": messages,
        }
        if self.tools:
            create_kwargs["tools"] = self.tools

        try:
            response = self.anthropic.messages.create(**create_kwargs)
        except anthropic.AuthenticationError as e:
            raise RuntimeError(f"Anthropic API key invalid or expired: {e}") from e
        except anthropic.RateLimitError as e:
            raise RuntimeError(f"Anthropic rate limit exceeded: {e}") from e
        except anthropic.BadRequestError as e:
            raise RuntimeError(f"Anthropic bad request (check CLAUDE_MODEL='{Config.CLAUDE_MODEL}'): {e}") from e
        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}") from e

        # Process tool uses
        while response.stop_reason == "tool_use":
            # Extract tool uses from response
            tool_results = []

            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input
                    tool_use_id = content_block.id

                    # Execute the tool
                    result = self._execute_tool(tool_name, tool_input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": json.dumps(result)
                    })

            # Add assistant response and tool results to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue the conversation
            followup_kwargs: Dict = {
                "model": Config.CLAUDE_MODEL,
                "max_tokens": 4096,
                "system": self._get_system_prompt(),
                "messages": messages,
            }
            if self.tools:
                followup_kwargs["tools"] = self.tools
            try:
                response = self.anthropic.messages.create(**followup_kwargs)
            except anthropic.AuthenticationError as e:
                raise RuntimeError(f"Anthropic API key invalid or expired: {e}") from e
            except anthropic.RateLimitError as e:
                raise RuntimeError(f"Anthropic rate limit exceeded: {e}") from e
            except anthropic.BadRequestError as e:
                raise RuntimeError(f"Anthropic bad request (check CLAUDE_MODEL='{Config.CLAUDE_MODEL}'): {e}") from e
            except anthropic.APIStatusError as e:
                raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}") from e

        # Extract final text response
        final_response = ""
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                final_response += content_block.text

        return {
            "output": final_response,
            "messages": messages,
            "response": response
        }
