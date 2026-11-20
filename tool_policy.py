READ_TOOLS = ["list_unread_emails", "get_email"]


def allowed_tools_for_task(user_task: str) -> list[str]:
    """Return the tools allowed for the user's current task."""
    task = user_task.casefold()

    if "summarize" in task:
        return READ_TOOLS

    return READ_TOOLS