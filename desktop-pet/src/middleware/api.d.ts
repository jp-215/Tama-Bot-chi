import { AxiosInstance } from 'axios'

interface Message {
    from: string
    text: string
    timestamp: number
}

interface Summary {
    who: string
    intent: string
    requirements: string[]
    urgency: string
    sentiment: string
    action_items: string[]
    one_liner: string
}

interface Conversation {
    sender: string
    conversation_id: string
    started_at: number
    last_activity: number
    messages: Message[]
    read: boolean
    summary: Summary | null
}

interface CalendarEvent {
    title: string
    start: string
    end: string
    calendar: string
    notes: string
}

interface Reminder {
    name: string
    due: string | null
    list: string
    body: string
}

interface ScheduleEventPayload {
    title: string
    start_iso: string
    end_iso: string
    notes: string
    calendar_name: string
}

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
}

interface ConversationsResponse {
    conversations: Conversation[]
    unread_count: number
}

interface UnreadConversationsResponse {
    conversations: Conversation[]
}

interface MarkReadResponse {
    success: boolean
}

interface CalendarEventsResponse {
    events: CalendarEvent[]
    permission_error?: string
}

interface RemindersResponse {
    reminders: Reminder[]
    permission_error?: string
}

interface SummarizeAllResponse {
    [conversation_id: string]: Summary
}

interface ChatResponse {
    reply: string
}

export function fetchAllConversations(): Promise<ConversationsResponse>
export function fetchUnreadConversations(): Promise<UnreadConversationsResponse>
export function fetchUnreadCount(): Promise<number>
export function markConversationRead(conversationId: string): Promise<MarkReadResponse>
export function markAllRead(): Promise<MarkReadResponse>
export function summarizeConversation(conversationId: string): Promise<Summary>
export function summarizeAll(): Promise<SummarizeAllResponse>
export function checkHealth(): Promise<boolean>
export function fetchCalendarEvents(days?: number): Promise<CalendarEventsResponse>
export function fetchReminders(): Promise<RemindersResponse>
export function scheduleEvent(data: ScheduleEventPayload): Promise<MarkReadResponse>
export function chatWithTamaBotchi(message: string, history?: ChatMessage[]): Promise<ChatResponse>

declare const api: AxiosInstance
export default api
