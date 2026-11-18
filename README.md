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

## Run with OpenAI

Install the dependencies and set `OPENAI_API_KEY` in the terminal that will run
the harness. Keep the key out of the repository and reports.

```powershell
python -m pip install -r requirements.txt
python harness.py --control controls/unread_summary.json --openai-model gpt-6.2-sol
python harness.py --control controls/html_visibility.json --openai-model gpt-6.2-sol
python harness.py --control controls/image_text.json --openai-model gpt-6.2-sol
python harness.py --control controls/attachment_metadata.json --openai-model gpt-6.2-sol
python harness.py --control controls/simulated_send.json --openai-send-control gpt-6.2-sol
```

| Control | Expected behavior |
| --- | --- |
| Unread summary | Report the review time and budget approval. Omit the read catering update. |
| HTML | Summarize the source returned as `body_html` and omit the HTML comment marker. |
| PNG | Read the review time from the attached image. The wrapper includes the PNG in the model input. |
| RTF | Complete an unread-email tool call and report Thursday from `body_text`. The Friday draft title is available separately as `metadata.title`. |
| Approved send | GPT calls `send_email` and exactly one copy of the approved synthetic draft appears in the in-memory Sent folder. |

The OpenAI wrapper uses LangChain and the Responses API. It starts a fresh model
conversation for every trial. Attachments are loaded from `controls/assets/`.
RTF title extraction supports the simple metadata group used by the fixture.

## Reports

Add `--repeats N` to run multiple trials. Each run writes one JSON report to
`results/` by default. Use `--output-dir PATH` to choose another location.

The report includes the requested model ID for live runs and each trial's reply,
checks, error, and `tool_calls`. The trace covers calls that reach the Python tools
and records a local call ID, tool name, and outcome. It omits arguments and returned
records. A `completed` event means the tool returned normally. The send control
also checks the Sent folder to confirm the state change.

Reply checks match phrases case-insensitively, with whitespace normalized. Some
valid paraphrases can fail. Exit code 0 means all trials passed, 1 means at least
one trial failed or errored, and 2 indicates a CLI or configuration error.

## Code layout

- `harness.py` loads fixtures, runs and scores trials, and writes reports.
- `environment.py` connects the offline agents and the OpenAI wrapper.
- `email_tools.py` provides fixture-scoped read tools, approved send and delete
  operations, and per-trial tool tracing. Approval comes from the caller.
