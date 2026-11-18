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

## Agent interface

`environment.py` accepts a callable that takes `user_task` and `emails` as separate
arguments and returns the final reply as a string. The future LangChain wrapper can
implement that interface. To try a callable before it is wired into the CLI, pass it
to `harness.run_control` as the `agent` argument.

Each trial receives a fresh copy of the email records. The harness reuses the supplied
callable across repeats and leaves conversation memory to the agent. Reports store
the final text under `response` and any invocation exception under `error`.

The older fixtures in `seeds/` and the sample mailbox report in `results/` document
the previous prototype. The current CLI runs the JSON control in `controls/`.
