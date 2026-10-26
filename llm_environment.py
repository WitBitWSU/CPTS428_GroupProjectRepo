""" copy of mock_environment.py with a change to invoke_agent() method 
to run sampleApp.py
"""
import copy
import sampleApp


class MockMailbox:
    """What the stub agents use as their email tools."""

    def __init__(self, emails=()):
        self.inbox = copy.deepcopy(list(emails))
        self.deleted, self.sent, self.flagged = [], [], set()

    def list_emails(self):
        return [{k: e[k] for k in ("id", "sender", "subject")} for e in self.inbox]

    def read_email(self, email_id):
        return next(e for e in self.inbox if e["id"] == email_id)

    def send_email(self, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})

    def delete_email(self, email_id):
        for e in self.inbox:
            if e["id"] == email_id:
                self.inbox.remove(e)
                self.deleted.append(email_id)
                return

    def flag_email(self, email_id):
        self.flagged.add(email_id)

    def state(self):
        return {"inbox_count": len(self.inbox),
                "inbox_ids": [e["id"] for e in self.inbox],
                "deleted_ids": list(self.deleted),
                "flagged_ids": sorted(self.flagged),
                "sent": copy.deepcopy(self.sent)}


_mailbox = MockMailbox()


def reset_mailbox():
    global _mailbox
    _mailbox = MockMailbox()


def populate_mailbox(emails):
    global _mailbox
    _mailbox = MockMailbox(emails)


def invoke_agent(user_task):
    return sampleApp.run_email_assistant(user_task, mailbox)


def read_mailbox_state():
    return _mailbox.state()
