"""Simulated email tools scoped to the records and approvals for one trial."""

from copy import deepcopy


class EmailTools:
    """Bind tool calls to one fixture's email records."""

    def __init__(self, emails, *, approved_deletions=(), approved_sends=()):
        self._emails = deepcopy(emails)
        # The wrapper supplies approvals from the user's request or confirmation.
        self._approved_deletions = set(approved_deletions)
        self._approved_sends = list(approved_sends)
        self._sent = []
        self._trash = []

    def list_unread_emails(self) -> list[dict]:
        """Return unread email records in their original order."""
        # Tool callers receive copies, so they cannot change the stored records.
        return [deepcopy(email) for email in self._emails if email["unread"]]

    def get_email(self, email_id: str) -> dict | None:
        """Read an email by fixture ID, or return None if the ID is unknown."""
        for email in self._emails:
            if email["id"] == email_id:
                return deepcopy(email)
        return None

    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Record an approved outgoing message in the simulated sent folder."""
        message = (to, subject, body)
        if message not in self._approved_sends:
            raise PermissionError("This outgoing message has not been approved")

        # Each approval permits one simulated delivery of the exact message.
        self._approved_sends.remove(message)
        record = {"to": to, "subject": subject, "body": body}
        self._sent.append(record)
        return record.copy()

    def delete_email(self, email_id: str) -> bool:
        """Move an approved email to the simulated trash if it exists."""
        if email_id not in self._approved_deletions:
            raise PermissionError("Deletion of this email has not been approved")

        for index, email in enumerate(self._emails):
            if email["id"] == email_id:
                self._trash.append(self._emails.pop(index))
                self._approved_deletions.remove(email_id)
                return True
        return False

    def action_state(self) -> dict:
        """Return a snapshot for the wrapper or the harness."""
        return deepcopy({"sent": self._sent, "trash": self._trash})
