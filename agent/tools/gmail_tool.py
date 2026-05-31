"""
Gmail Tool for sending emails, managing labels, and handling calendar events.
"""

import os
import pickle
import logging
from datetime import datetime, timedelta
from typing import Optional, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64

from config import Config
from tama_types import EmailSendResponse, CalendarEventResponse, BusyTimeSlot
from exceptions import GmailAuthError, GmailSendError, CalendarEventError

logger = logging.getLogger(__name__)

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

EMAIL_PREVIEW_LENGTH = 200


class GmailTool:
    """Tool for Gmail email and calendar operations"""

    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.gmail_service = None
        self.calendar_service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Gmail and Calendar APIs."""
        try:
            if os.path.exists(Config.GMAIL_TOKEN_PATH):
                with open(Config.GMAIL_TOKEN_PATH, "rb") as token_file:
                    self.creds = pickle.load(token_file)

            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(Config.GMAIL_CREDENTIALS_PATH):
                        raise GmailAuthError(f"Gmail credentials not found at {Config.GMAIL_CREDENTIALS_PATH}")

                    flow = InstalledAppFlow.from_client_secrets_file(Config.GMAIL_CREDENTIALS_PATH, SCOPES)
                    self.creds = flow.run_local_server(port=0)

                os.makedirs(os.path.dirname(Config.GMAIL_TOKEN_PATH), exist_ok=True)
                with open(Config.GMAIL_TOKEN_PATH, "wb") as token_file:
                    pickle.dump(self.creds, token_file)

            self.gmail_service = build("gmail", "v1", credentials=self.creds)
            self.calendar_service = build("calendar", "v3", credentials=self.creds)

            logger.info("Successfully authenticated with Gmail and Calendar APIs")

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise GmailAuthError(f"Failed to authenticate with Gmail/Calendar: {e}") from e

    # ------------------- Gmail Methods -------------------

    def send_email(self, to: str, subject: str, body: str, html: bool = False) -> EmailSendResponse:
        """Send an email via Gmail."""
        try:
            message = MIMEText(body, "html" if html else "plain")
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = self.gmail_service.users().messages().send(
                userId="me", body={"raw": raw}
            ).execute()

            logger.info(f"Email sent to {to}")
            return {"success": True, "message_id": result["id"], "recipient": to, "error": None}

        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise GmailSendError(f"Gmail API error: {e}") from e
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise GmailSendError(f"Failed to send email: {e}") from e

    # ------------------- Calendar Methods -------------------

    def create_calendar_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendees: List[str],
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> CalendarEventResponse:
        """Create a calendar event."""
        try:
            event = {
                "summary": summary,
                "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
                "attendees": [{"email": email} for email in attendees],
            }
            if description:
                event["description"] = description
            if location:
                event["location"] = location

            result = self.calendar_service.events().insert(
                calendarId="primary", body=event, sendUpdates="all"
            ).execute()

            logger.info(f"Created calendar event: {summary}")
            return {"success": True, "event_id": result["id"], "event_link": result.get("htmlLink"), "attendees": attendees, "error": None}

        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            raise CalendarEventError(f"Failed to create calendar event: {e}") from e

    def get_availability(self, start_date: datetime, end_date: datetime, calendar_id: str = "primary") -> List[BusyTimeSlot]:
        """Get busy times in the specified date range."""
        try:
            body = {
                "timeMin": start_date.isoformat() + "Z",
                "timeMax": end_date.isoformat() + "Z",
                "items": [{"id": calendar_id}],
            }
            events_result = self.calendar_service.freebusy().query(body=body).execute()
            return events_result["calendars"][calendar_id]["busy"]
        except Exception as e:
            logger.error(f"Failed to get calendar availability: {e}")
            return []

    def find_free_slot(self, duration_minutes: int = 30, days_ahead: int = 7, calendar_id: str = "primary") -> Optional[datetime]:
        """Find the next available free slot of given duration."""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=days_ahead)
        busy_times = self.get_availability(start_date, end_date, calendar_id=calendar_id)

        current_time = start_date
        for busy_slot in busy_times:
            try:
                slot_start = datetime.fromisoformat(busy_slot["start"].replace("Z", "+00:00"))
                if (slot_start - current_time).total_seconds() >= duration_minutes * 60:
                    return current_time
                current_time = datetime.fromisoformat(busy_slot["end"].replace("Z", "+00:00"))
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid busy slot format: {e}")
                continue

        if (end_date - current_time).total_seconds() >= duration_minutes * 60:
            return current_time

        return None
