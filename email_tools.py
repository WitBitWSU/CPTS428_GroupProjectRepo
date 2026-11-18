"""Read-only tools scoped to the email records supplied for one trial."""

from copy import deepcopy


class EmailTools:
    """Bind tool calls to one fixture's email records."""

    def __init__(self, emails):
        self._emails = deepcopy(emails)

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
