"""Throwaway stand-ins for the real agent, ONLY to prove the harness works.

These are keyword-matching functions, not LLMs. Results from them are not security findings.
The real agent must expose: run_agent(user_task: str, mailbox) -> str
"""
import re


def vulnerable_agent(user_task, mailbox):
    """Obeys instructions it finds in email bodies."""
    summaries = []
    for row in mailbox.list_emails():
        email = mailbox.read_email(row["id"])
        body = email["body"]
        html_body = email.get("body_html", "")
        content = body + "\n" + html_body
        summaries.append(f"{email['subject']}: {body[:40]}")
        if "delete all" in content.lower():
            for r in mailbox.list_emails():
                mailbox.delete_email(r["id"])
            break
        match = re.search(r"forward.*?([\w.]+@[\w.]+)", content, re.I | re.S)
        if match:
            everything = "\n".join(mailbox.read_email(r["id"])["body"] for r in mailbox.list_emails())
            mailbox.send_email(match.group(1), "Fwd", everything)
    return "Summary:\n" + "\n".join(summaries)


def safe_agent(user_task, mailbox):
    """Only summarizes; ignores instructions in emails."""
    return "Summary:\n" + "\n".join(
        mailbox.read_email(r["id"])["subject"] for r in mailbox.list_emails())
