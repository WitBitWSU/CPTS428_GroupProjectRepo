"""Simulated email tools scoped to the records and approvals for one trial."""

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
from uuid import uuid4


_tool_trace = ContextVar("email_tool_trace", default=None)
_tools_holder = ContextVar("email_tools_holder", default=None)


@contextmanager
def capture_action_state():
    """Keep a handle on the trial's EmailTools so the harness can read its final state.

    The agent builds its tools internally, so the harness cannot see the Sent and Trash
    folders on its own. EmailTools registers itself in the yielded dict under "tools".
    """
    holder = {}
    token = _tools_holder.set(holder)
    try:
        yield holder
    finally:
        _tools_holder.reset(token)


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

    def __init__(self, emails, *, approved_deletions=(), approved_sends=(),
                 enforce_approvals=True):
        """Copy fixture inputs and start with empty Sent and Trash folders.

        With enforce_approvals=False the tools act on every request, like an agent
        with no approval step. Only the undefended baseline uses that setting.
        """
        self._enforce_approvals = enforce_approvals
        holder = _tools_holder.get()
        if holder is not None:
            holder["tools"] = self
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
    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Record an approved outgoing message in the simulated sent folder."""
        message = (to, subject, body)
        approved = message in self._approved_sends
        if self._enforce_approvals and not approved:
            raise PermissionError("This outgoing message has not been approved")

        # Each approval permits one simulated delivery of the exact message.
        if approved:
            self._approved_sends.remove(message)
        record = {"to": to, "subject": subject, "body": body}
        self._sent.append(record)
        return record.copy()

    @trace_tool
    def delete_email(self, email_id: str) -> bool:
        """Move an approved email to the simulated trash if it exists."""
        if self._enforce_approvals and email_id not in self._approved_deletions:
            raise PermissionError("Deletion of this email has not been approved")

        for index, email in enumerate(self._emails):
            if email["id"] == email_id:
                # Move the record and consume approval only when the message exists.
                self._trash.append(self._emails.pop(index))
                self._approved_deletions.discard(email_id)
                return True
        return False

    def action_state(self) -> dict:
        """Copy Sent and Trash so report callers cannot change simulator state."""
        return deepcopy({"sent": self._sent, "trash": self._trash})
