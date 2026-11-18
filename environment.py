"""Adapter for passing JSON email records to the agent."""

from email_tools import EmailTools


def invoke_json_agent(user_task, emails, *, agent=None):
    """Pass a JSON fixture to an agent and return its final text reply."""
    if agent is None:
        raise NotImplementedError("No JSON agent configured. Use --demo-control for the fake agent.")

    # The future LangChain wrapper will format these separate inputs and extract the final reply.
    reply = agent(user_task, emails)
    if not isinstance(reply, str):
        raise TypeError("The JSON agent must return its final reply as text")
    return reply


def demo_unread_summary(user_task, emails):
    """Deterministic fake for verifying the read-only control pipeline."""
    tools = EmailTools(emails)
    return " ".join(email["body"] for email in tools.list_unread_emails())
