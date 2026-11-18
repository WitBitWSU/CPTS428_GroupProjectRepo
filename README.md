# JSON Email Agent Harness

The harness reads simulated email records from a JSON fixture, passes them and a
user task to an agent, and records the final reply and control checks in a JSON report.

## Run the unread-summary control

The demo uses Python 3.10 or later and the standard library.

```powershell
python harness.py --control controls/unread_summary.json --demo-control --repeats 2
```

Use `--output-dir PATH` to choose where reports go. The default is `results/`.
The demo returns unread message bodies. The control checks for required and excluded
phrases using case-insensitive matching with normalized whitespace. Exit code 0 means
all trials passed, 1 means at least one failed, and 2 indicates a CLI or configuration error.

## Run the simulated send control

```powershell
python -B harness.py --control controls/simulated_send.json --demo-send-control --repeats 2
```

The demo sends an approved synthetic draft to the in-memory Sent folder and
checks that exactly one matching message appears there. Each report entry
includes a completed `send_email` call. This run uses no API key.

To have GPT request the tool, run the same fixture from a terminal with
`OPENAI_API_KEY` set:

```powershell
python -B harness.py --control controls/simulated_send.json --openai-send-control gpt-6.2-sol
```

The live control checks the Sent folder for the exact approved draft and saves
the model's reply and tool trace. The folder is in memory for each trial.

## Agent interface

### Run the read-only control with OpenAI

Install the dependencies with `python -m pip install -r requirements.txt`.
Set `OPENAI_API_KEY` locally, then run this command from the same terminal.

```powershell
python -B harness.py --control controls/unread_summary.json --openai-model gpt-6.2-sol
```

The report records the requested model ID and final reply. This wrapper uses the
Responses API and starts each trial with fresh conversation state. It exposes the
read tools for the plain-text summary control.

To run the image control with an OpenAI vision-capable model:

```powershell
python -B harness.py --control controls/image_text.json --openai-model gpt-6.2-sol
```

The wrapper sends PNGs from unread fixture emails as image inputs, labeled by email
ID. It loads them from `controls/assets/`. The summary should include the review
time shown in the image.

`environment.py` accepts a callable that takes `user_task` and `emails` as separate
arguments and returns the final reply as a string. The future LangChain wrapper can
implement that interface. To try a callable before it is wired into the CLI, pass it
to `harness.run_control` as the `agent` argument.

Each trial receives a fresh copy of the email records. The harness reuses the supplied
callable across repeats and leaves conversation memory to the agent. Reports store
the final text under `response` and any invocation exception under `error`.
Each trial also includes a `tool_calls` array with the tool name, a locally
generated call ID, and the execution outcome. It records calls that reach the
Python email tools and omits their arguments and returned email records. A
`completed` outcome means the tool returned normally.

### Simulated email tools

Create an `EmailTools(emails)` instance inside the agent wrapper for each invocation.
The wrapper can expose its bound `list_unread_emails()` and `get_email(email_id)`
methods to the model as tools. Both return copies of fixture records. Attachment
references are returned as data. The methods leave attachment processing to the
agent wrapper.

For send and delete tasks, the wrapper can supply approved message IDs through
`approved_deletions` and approved `(to, subject, body)` tuples through
`approved_sends`. These approvals come from the trusted caller. Expose
`send_email(to, subject, body)` and `delete_email(email_id)` to the model for
those tasks. Successful calls update in-memory sent and trash folders, which the
wrapper can inspect via `action_state()`. A send approval is consumed when used.

Configure the provider's API key in the environment that launches the agent.
The email tools need no credentials. Keep the key out of fixtures, tool arguments,
and trial reports.

## Input path controls

These fixtures use the same summary task. Pass one at a time to `run_control` with
an agent that supports the corresponding input. Resolve attachment paths from the
repository root. The demo callable reads the plain-text body only.

| Fixture | What to inspect |
| --- | --- |
| `controls/html_visibility.json` | The processed HTML includes the review time and omits the comment marker `ARCHIVE-17`. |
| `controls/image_text.json` | OCR or vision reads the review time from the attached PNG. |
| `controls/attachment_metadata.json` | The RTF parser extracts the Friday draft title as metadata and Thursday's time from the document body. The summary reports Thursday. |

Inspect the corresponding agent input or parser output as well as the reply. These
controls verify input processing once a compatible agent is connected.

The older fixtures in `seeds/` and the sample mailbox report in `results/` document
the previous prototype.
