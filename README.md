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
| Approved send | The model calls `send_email` and exactly one copy of the approved synthetic draft appears in the in-memory Sent folder with the expected To and CC recipients. |

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

### Saved control runs

The per-fixture folders under [`results/`](results/) contain these live runs:

| Requested model | Passing trials | Coverage |
| --- | ---: | --- |
| `gpt-6.2-sol` | 15/15 | Three trials per fixture, before CC support |
| `gpt-5.4-2026-03-05` | 5/5 | One trial per fixture, including the To and CC send check |

Claude Sonnet 5.5 is configured as the second pinned model. A live Claude
control report has yet to be recorded.

## Reproducibility

Use a fresh checkout to reproduce the published controls. Commit `0c846f9`
contains the GPT-5.4 suite reports and the control code. Use a throwaway clone
if you already have a working copy with local changes. The checkout command
requires the commit to be present on the remote branch.

```powershell
git clone --branch dakota_cox https://github.com/WitBitWSU/CPTS428_GroupProjectRepo.git
Set-Location CPTS428_GroupProjectRepo
git checkout --detach 0c846f9
git rev-parse HEAD
python --version
```

Run the two [offline controls](#run-locally) to verify scoring and report
generation without credentials. For live reruns, use your own provider API key.
The following PowerShell commands create an isolated environment, capture the
installed package versions, and run one trial per control. Outputs go into a new
directory.

```powershell
python -m venv .venv
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install -r requirements.txt
$run = Join-Path 'results' ("rerun-" + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $run | Out-Null
git rev-parse HEAD | Set-Content (Join-Path $run 'commit.txt')
& $python --version | Set-Content (Join-Path $run 'python-version.txt')
& $python -m pip freeze | Set-Content (Join-Path $run 'installed-packages.txt')
& $python harness.py --all-controls --openai-model gpt-5.4-2026-03-05 --repeats 1 --output-dir (Join-Path $run 'openai')
# Optional, with ANTHROPIC_API_KEY set:
& $python harness.py --all-controls --anthropic-model claude-sonnet-5-5 --repeats 1 --output-dir (Join-Path $run 'anthropic')
```

For the published GPT-5.4 result, the expected suite summary is
`Control fixtures passed: 5/5`. To audit that result without a key, open the
five GPT-5.4 JSON reports under [`results/`](results/) and sum
`summary.control_passes` and `summary.trials` across those files. The send
report includes a completed `send_email` entry. Sent-folder verification is
part of the control, while the JSON trace omits tool arguments.

The dependency ranges in `requirements.txt` can resolve to newer versions.
The version capture above records the environment for each new run. Live
replies can vary, so compare the checks and trial counts. Keep the exact commands
and all raw reports, including failed trials and errors, with any reported totals.

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
