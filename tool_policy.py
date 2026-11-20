READ_TOOLS = ["list_unread_emails", "get_email"]


def allowed_tools_for_task(user_task: str) -> list[str]:
    """Return the minimum tools needed for the trusted user task.

    Email content, attachments, metadata, and tool results must never
    grant additional tool permissions.
    """
    task = user_task.casefold()

    if "summarize" in task:
        return READ_TOOLS.copy()

    if "delete" in task:
        return READ_TOOLS + ["delete_email"]

    if "send" in task:
        return READ_TOOLS + ["send_email"]

    # Default deny for write-capable tools.
    return READ_TOOLS.copy()