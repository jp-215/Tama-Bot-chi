"""
Type definitions for TamaBotchi agent.
All data structures used across the application.
"""
from typing import TypedDict, List, Dict, Optional, Literal


# User and Profile Types

class ContactInfo(TypedDict):
    """Contact information for a user"""
    phone: Optional[str]
    email: Optional[str]
    linkedin: Optional[str]


class UserProfile(TypedDict):
    """Complete user profile structure"""
    user_id: str
    name: str
    email: str
    role: str
    industry: str
    seniority: str
    interests: List[str]
    goals: List[str]
    contact: ContactInfo


class ConversationStyle(TypedDict):
    """User's communication style preferences"""
    tone: str  # "casual", "professional", "friendly"
    length: str  # "brief", "moderate", "detailed"
    formality: str  # "informal", "semi-formal", "formal"
    emoji_usage: bool


class PermissionSettings(TypedDict):
    """User permission settings for each action type"""
    send_message: str  # PermissionLevel enum value
    schedule_meeting: str
    send_email: str
    share_profile: str
    request_connection: str


class UserPreferences(TypedDict):
    """User preferences and settings"""
    user_id: str
    conversation_style: ConversationStyle
    permissions: PermissionSettings
    high_match_threshold: float
    auto_schedule_enabled: bool


# Message and Conversation Types

class MessageMetadata(TypedDict, total=False):
    """Optional metadata for messages"""
    generated_by_agent: bool
    match_score: Optional[float]
    action_taken: Optional[str]


class ConversationMessage(TypedDict):
    """Single message in a conversation"""
    message_id: str
    sender: str
    recipient: str
    message: str
    timestamp: float
    metadata: MessageMetadata


class ConversationHistory(TypedDict):
    """Complete conversation history"""
    conversation_id: str
    participants: List[str]
    messages: List[ConversationMessage]
    created_at: float
    last_message_at: float


# Matching and Detection Types

class MatchResult(TypedDict):
    """Result of compatibility matching"""
    score: float
    is_high_match: bool
    reason: str
    breakdown: Dict[str, float]  # "interests": 0.8, "industry": 0.6, etc.


class DetectionContext(TypedDict):
    """Context about how/where a user was detected"""
    event_name: Optional[str]
    location: Optional[str]
    detection_method: str  # "multipeer", "wifi", "event_api"
    timestamp: str
    additional_info: Dict[str, str]


# Action and Response Types

ActionType = Literal[
    "send_message",
    "schedule_meeting",
    "send_email",
    "share_profile",
    "request_connection"
]

PermissionLevel = Literal[
    "always_ask",
    "auto_high_match",
    "always_auto",
    "never"
]


class SendMessageResult(TypedDict):
    """Result of sending a message"""
    success: bool
    recipient: str
    message: str
    method: str  # "imessage" or "email"
    sent_at: str
    error: Optional[str]


class ScheduleMeetingResult(TypedDict):
    """Result of scheduling a meeting"""
    success: bool
    event_id: Optional[str]
    event_link: Optional[str]
    summary: str
    start_time: str
    end_time: str
    attendees: List[str]
    error: Optional[str]


class DetectionResponse(TypedDict):
    """Response when a user is detected nearby"""
    action: str  # "sent_imessage", "sent_email", "request_permission", "skip", "no_contact_method"
    recipient: Optional[str]
    message: Optional[str]
    success: Optional[bool]
    reason: Optional[str]
    match_score: Optional[float]
    other_user: Optional[UserProfile]
    context: Optional[DetectionContext]


class IncomingMessageResponse(TypedDict):
    """Response to an incoming message"""
    response: str
    should_notify_user: bool
    conversation_id: str
    action_taken: Optional[str]


# Template Types

class MessageTemplate(TypedDict):
    """Template for generating messages"""
    template_id: str
    template_type: str  # "introduction", "follow_up", "meeting_request"
    content: str
    variables: List[str]
    tone: str


# MCP Server Response Types

class MCPHealthCheck(TypedDict):
    """Health check response from MCP server"""
    status: str
    services: Dict[str, bool]
    timestamp: str


class CacheEntry(TypedDict):
    """Cache entry from Redis"""
    key: str
    value: str
    ttl: Optional[int]


class InteractionLog(TypedDict):
    """Log entry for user interaction"""
    interaction_id: str
    user_id: str
    other_user_id: str
    interaction_type: str
    timestamp: float
    metadata: Dict[str, any]


# API Request/Response Types

class UserDetectedRequest(TypedDict):
    """Request body for user detected endpoint"""
    user_id: str
    other_user_id: str
    context: DetectionContext


class IncomingMessageRequest(TypedDict):
    """Request body for incoming message endpoint"""
    user_id: str
    sender_id: str
    message: str
    conversation_id: str


class SendMessageRequest(TypedDict):
    """Request body for send message endpoint"""
    user_id: str
    recipient_id: str
    message: str


class TaskRequest(TypedDict):
    """Request body for task execution endpoint"""
    user_id: str
    task: str


class HealthResponse(TypedDict):
    """Health check response"""
    status: str
    timestamp: str
    services: Dict[str, bool]


# iMessage Server Types

class iMessageSendRequest(TypedDict):
    """Request to send iMessage"""
    recipient: str
    message: str


class iMessageSendResponse(TypedDict):
    """Response from iMessage send"""
    success: bool
    recipient: Optional[str]
    message: Optional[str]
    sent_at: Optional[str]
    error: Optional[str]


class iMessageHistory(TypedDict):
    """iMessage from Messages database"""
    id: int
    text: Optional[str]
    timestamp: float
    is_from_me: bool
    sender: str


# Gmail/Calendar Types

class EmailSendRequest(TypedDict):
    """Request to send email"""
    to: str
    subject: str
    body: str
    html: bool


class EmailSendResponse(TypedDict):
    """Response from email send"""
    success: bool
    message_id: Optional[str]
    recipient: Optional[str]
    error: Optional[str]


class CalendarEventRequest(TypedDict):
    """Request to create calendar event"""
    summary: str
    start_time: str  # ISO format
    duration_minutes: int
    attendees: List[str]
    description: Optional[str]
    location: Optional[str]


class CalendarEventResponse(TypedDict):
    """Response from calendar event creation"""
    success: bool
    event_id: Optional[str]
    event_link: Optional[str]
    attendees: Optional[List[str]]
    error: Optional[str]


class BusyTimeSlot(TypedDict):
    """Busy time slot from calendar"""
    start: str  # ISO format
    end: str  # ISO format


# Error Types

class ErrorResponse(TypedDict):
    """Standard error response"""
    error: str
    error_type: str
    details: Optional[Dict[str, any]]
    timestamp: str
