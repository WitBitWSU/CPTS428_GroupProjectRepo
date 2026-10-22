"""Integration points between the harness and the REAL email client + agent.

The harness (harness.py) knows nothing about Gmail, IMAP, or how the agent is launched.
Everything environment-specific lives in these four functions. They are intentionally
unimplemented: the email client and agent do not exist yet. Each raises NotImplementedError
(instead of silently doing nothing) so a run can never report results from an environment
that was never actually driven.

To try the harness today, use the in-memory demo instead:
    python harness.py seeds/delete_all.json --env mock_environment

Mailbox state contract (what read_mailbox_state must return):
    {
      "inbox_count":  int,         # messages currently in the inbox
      "inbox_ids":    [str, ...],  # their IDs
      "deleted_ids":  [str, ...],  # messages that were deleted / moved to trash
      "flagged_ids":  [str, ...],  # messages that are flagged/starred
      "sent":         [{"to": str, "subject": str, "body": str}, ...]  # outbound mail
    }
IDs must match the "id" values used in the seed file's mailbox list.
"""


def reset_mailbox():
    """Put the test email account into a known empty state before each trial.

    TODO (real client): delete/trash all messages in the inbox, sent folder, and trash of the
    dedicated TEST account, and clear flags. Never point this at a personal account.
    """
    raise NotImplementedError("reset_mailbox() is not implemented yet (see environment.py)")


def populate_mailbox(emails):
    """Load the seed's emails into the test account.

    Args:
        emails: list of dicts from the seed file's "mailbox" field, each with at least
                id, sender, subject, body (and any extra fields the seed defines).

    TODO (real client): insert each message so it appears as a received, unread inbox message
    from `sender`, and remember the mapping from seed id -> the client's real message id so
    read_mailbox_state() can report seed ids.
    """
    raise NotImplementedError("populate_mailbox() is not implemented yet (see environment.py)")


def invoke_agent(user_task):
    """Give the agent the legitimate user's task and wait until it finishes.

    Args:
        user_task: e.g. "Summarize my unread emails."

    Returns:
        The agent's final text reply as a string.

    TODO (real agent): send user_task to the agent (function call, HTTP request, or UI/CLI
    driver), block until it is done or a timeout passes, and return its reply.
    """
    raise NotImplementedError("invoke_agent() is not implemented yet (see environment.py)")


def read_mailbox_state():
    """Report the test account's current state, using the contract in the module docstring.

    TODO (real client): query the account (IMAP/Gmail API/database) for inbox, trash, flags,
    and sent messages, translating real message ids back to seed ids.
    """
    raise NotImplementedError("read_mailbox_state() is not implemented yet (see environment.py)")
