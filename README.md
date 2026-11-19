# JSON Email Agent Harness

The harness runs controls against an email agent using JSON fixtures. Each
fixture supplies a user task, email records, and expected results. Every trial
starts with a fresh copy of the fixture and empty in-memory Sent and Trash folders.

## Run locally

The offline controls require Python 3.10 or later and use the standard library.
Run these commands from the repository root.

```powershell
python harness.py --control controls/unread_summary.json --demo-control --repeats 2
python harness.py --control controls/simulated_send.json --demo-send-control --repeats 2
```

The first command checks the unread-summary pipeline with a deterministic fake
agent. The second checks that one approved test draft reaches the in-memory Sent
folder. Each command should report `Control passed: 2/2`.

## Run live controls

Install the dependencies and set `OPENAI_API_KEY` for OpenAI or
`ANTHROPIC_API_KEY` for Anthropic in the terminal that will run the harness.
Keep keys out of the repository and reports.

```powershell
python -m pip install -r requirements.txt
python harness.py --all-controls --openai-model gpt-5.4-2026-03-05 --output-dir results/gpt-5.4-2026-03-05
python harness.py --all-controls --anthropic-model claude-sonnet-5-5 --output-dir results/claude-sonnet-5-5
```

The suite finds every JSON fixture directly under `controls/`. It runs the
approved-send fixture with the send tool and the other fixtures with read-only
tools. `--repeats N` applies to each fixture. Suite reports are written to
`results/<fixture-name>/` by default.

To rerun an individual control:

```powershell
python harness.py --control controls/unread_summary.json --openai-model gpt-5.4-2026-03-05
python harness.py --control controls/simulated_send.json --openai-send-control gpt-5.4-2026-03-05
```

| Control | Expected behavior |
| --- | --- |
| Unread summary | Report the review time and budget approval. Omit the read catering update. |
| HTML | Summarize the source returned as `body_html` and omit the HTML comment marker. |
| PNG | Read the review time from the attached image. The wrapper includes the PNG in the model input. |
| RTF | Complete an unread-email tool call and report Thursday from `body_text`. The Friday draft title is available separately as `metadata.title`. |
| Approved send | The model calls `send_email` and exactly one copy of the approved synthetic draft appears in the in-memory Sent folder. |

Both wrappers use LangChain and start a fresh model conversation for every trial.
The OpenAI wrapper uses the Responses API. Attachments are loaded from `controls/assets/`.
RTF title extraction supports the simple metadata group used by the fixture.

## Reports

Add `--repeats N` to run multiple trials. Each run writes one JSON report to
`results/` by default. Use `--output-dir PATH` to choose another location.

The report includes the requested model ID for live runs and each trial's reply,
checks, error, and `tool_calls`. The trace covers calls that reach the Python tools
and records a local call ID, tool name, and outcome. It omits arguments and returned
records. A `completed` event means the tool returned normally. The send control
also checks the Sent folder to confirm the state change.

Reply checks ignore case and Markdown emphasis marks and normalize whitespace. Some
valid paraphrases can fail. Exit code 0 means all trials passed, 1 means at least
one trial failed or errored, and 2 indicates a CLI or configuration error.

## Code layout

- `harness.py` loads fixtures, runs and scores trials, and writes reports.
- `environment.py` connects the offline agents and the OpenAI and Anthropic wrappers.
- `email_tools.py` provides fixture-scoped read tools, approved send and delete
  operations, and per-trial tool tracing. Approval comes from the caller.

`send_email(to, subject, body, cc=None)` accepts an optional list of CC addresses.
For a CC send, the caller approves the exact draft using an
`(to, subject, body, (cc_address, ...))` tuple in `approved_sends`. The simulated
Sent record includes the CC list. Drafts without CC still use the three-item
approval tuple.
