"""Simulated email tools scoped to the records and approvals for one trial."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from uuid import uuid4


_tool_trace = ContextVar("email_tool_trace", default=None)


@contextmanager
def capture_tool_calls():
    """Collect tool executions for the current trial and reset on exit."""
    events = []
    token = _tool_trace.set(events)
    try:
        yield events
    finally:
        _tool_trace.reset(token)


def trace_tool(method):
    """Record an outcome at the tool boundary without storing arguments or results."""
    # Preserve the method's name, signature, and docstring for LangChain's tool schema.
    @wraps(method)
    def invoke(*args, **kwargs):
        events = _tool_trace.get()
        if events is None:
            return method(*args, **kwargs)

        event = {"tool": method.__name__, "call_id": uuid4().hex, "outcome": "started"}
        events.append(event)
        try:
            result = method(*args, **kwargs)
        except PermissionError:
            event["outcome"] = "blocked"
            raise
        except Exception:
            event["outcome"] = "error"
            raise
        event["outcome"] = "completed"
        return result

    return invoke


class EmailTools:
    """Own one trial's inbox, sent messages, trash, and action approvals."""

    def __init__(self, emails, *, approved_deletions=(), approved_sends=()):
        """Copy fixture inputs and start with empty Sent and Trash folders."""
        self._emails = deepcopy(emails)
        # The wrapper supplies approvals from the user's request or confirmation.
        self._approved_deletions = set(approved_deletions)
        self._approved_sends = list(approved_sends)
        self._sent = []
        self._trash = []

    @trace_tool
    def list_unread_emails(self) -> list[dict]:
        """Return unread email records in their original order."""
        # Tool callers receive copies, so they cannot change the stored records.
        return [deepcopy(email) for email in self._emails if email["unread"]]

    @trace_tool
    def get_email(self, email_id: str) -> dict | None:
        """Read an email by fixture ID, or return None if the ID is unknown."""
        for email in self._emails:
            if email["id"] == email_id:
                return deepcopy(email)
        return None

    @trace_tool
    def send_email(self, to: str, subject: str, body: str, cc: list[str] | None = None) -> dict:
        """Record an outgoing message with optional approved CC addresses."""
        recipients = tuple(cc or ())
        message = (to, subject, body, recipients) if recipients else (to, subject, body)
        approved = message in self._approved_sends
        # A CC changes who receives the message and always requires exact approval.
        if not approved:
            raise PermissionError("This outgoing message has not been approved")

        # Each approval permits one simulated delivery of the exact message.
        self._approved_sends.remove(message)
        record = {"to": to, "subject": subject, "body": body}
        if recipients:
            record["cc"] = list(recipients)
        self._sent.append(record)
        return deepcopy(record)

    @trace_tool
    def delete_email(self, email_id: str) -> bool:
        """Move an approved email to the simulated trash if it exists."""
        if email_id not in self._approved_deletions:
            raise PermissionError("Deletion of this email has not been approved")

        for index, email in enumerate(self._emails):
            if email["id"] == email_id:
                # Move the record and consume approval only when the message exists.
                self._trash.append(self._emails.pop(index))
                self._approved_deletions.remove(email_id)
                return True
        return False

    def action_state(self) -> dict:
        """Copy Sent and Trash so report callers cannot change simulator state."""
        return deepcopy({"sent": self._sent, "trash": self._trash})
