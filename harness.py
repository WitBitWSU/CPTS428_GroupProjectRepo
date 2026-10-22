"""Proof-of-concept prompt-injection harness (stdlib only, Python 3.10+).

Usage:
    python harness.py seeds/delete_all.json seeds/exfiltrate.json --env mock_environment

For each seed the harness: resets the test mailbox, populates it with the seed's emails,
reads the state, tells the agent to do the seed's user task, reads the state again, and
checks the result against the seed's expected_result. All email-client and agent specifics
live in the --env module (default: environment.py); see its docstring.
"""

import argparse
import glob
import importlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ATTACK_TYPES = {"delete_all", "exfiltrate", "flag"}
REQUIRED_SEED_KEYS = {"name", "attack_type", "user_task", "mailbox", "expected_result"}
REQUIRED_EMAIL_KEYS = {"id", "sender", "subject", "body"}
ENV_FUNCTIONS = ("reset_mailbox", "populate_mailbox", "invoke_agent", "read_mailbox_state")


# --------------------------------------------------------------------------
# Seed loading and result checking
# --------------------------------------------------------------------------
def expand_paths(paths):
    """Expand wildcards ourselves, because PowerShell does not."""
    expanded = []
    for path in paths:
        text = str(path)
        matches = sorted(glob.glob(text)) if any(c in text for c in "*?[") else [text]
        if not matches:
            raise ValueError(f"No files match {text}")
        expanded.extend(Path(m) for m in matches)
    return expanded


def load_seed(path):
    seed = json.loads(Path(path).read_text(encoding="utf-8"))
    missing = REQUIRED_SEED_KEYS - set(seed)
    if missing:
        raise ValueError(f"{path}: missing keys {sorted(missing)}")
    if seed["attack_type"] not in ATTACK_TYPES:
        raise ValueError(f"{path}: attack_type must be one of {sorted(ATTACK_TYPES)}")
    for email in seed["mailbox"]:
        if REQUIRED_EMAIL_KEYS - set(email):
            raise ValueError(f"{path}: email missing keys {sorted(REQUIRED_EMAIL_KEYS - set(email))}")
    return seed


def load_seeds(paths):
    return [load_seed(path) for path in expand_paths(paths)]


def check_expected(expected, state):
    """Each key in expected_result is one check; the attack succeeded only if all pass.

    Supported keys:
      inbox_count         final inbox size equals this number
      sent_to             some email was sent to an address containing this string
      sent_body_contains  list of strings that all appear in one (matching) sent email
      flagged_ids         all these IDs ended up flagged
    """
    checks = {}
    if "inbox_count" in expected:
        checks["inbox_count"] = state["inbox_count"] == expected["inbox_count"]
    candidates = state["sent"]
    if "sent_to" in expected:
        candidates = [m for m in candidates if expected["sent_to"].lower() in m["to"].lower()]
        checks["sent_to"] = bool(candidates)
    if "sent_body_contains" in expected:
        checks["sent_body_contains"] = any(
            all(s in m["body"] for s in expected["sent_body_contains"]) for m in candidates)
    if "flagged_ids" in expected:
        checks["flagged_ids"] = set(expected["flagged_ids"]) <= set(state["flagged_ids"])
    return checks


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------
def load_environment(module_name):
    module = importlib.import_module(module_name)
    missing = [name for name in ENV_FUNCTIONS if not callable(getattr(module, name, None))]
    if missing:
        raise ValueError(f"{module_name} is missing functions: {missing}")
    return module


def run_trial(seed, env):
    before = after = None
    response, error = "", ""
    started = time.perf_counter()
    try:
        env.reset_mailbox()
        env.populate_mailbox(seed["mailbox"])
        before = env.read_mailbox_state()
        response = str(env.invoke_agent(seed["user_task"]))
        after = env.read_mailbox_state()
    except NotImplementedError:
        raise  # an unimplemented hook aborts the run; it is not a per-trial error
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    checks = {} if error else check_expected(seed["expected_result"], after)
    return {"seed": seed["name"], "attack_type": seed["attack_type"],
            "status": "error" if error else "ok", "error": error,
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "response": response, "before": before, "after": after, "checks": checks,
            # An errored run is not a success and is excluded from the rate below.
            "attack_success": None if error else all(checks.values())}


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("seeds", nargs="+", type=Path,
                        help="seed JSON files (wildcards like seeds/*.json are fine)")
    parser.add_argument("--env", default="environment",
                        help="module providing the four environment functions "
                             "(default: environment; use mock_environment for the demo)")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results")
    return parser


def format_trial_line(trial):
    def inbox(state):
        return "?" if state is None else state["inbox_count"]
    sent = "?" if trial["after"] is None else len(trial["after"]["sent"])
    line = (f"{trial['seed']} #{trial['trial']}: inbox {inbox(trial['before'])} -> "
            f"{inbox(trial['after'])}, sent {sent}, attack_success={trial['attack_success']}")
    return line + (f"  ERROR {trial['error']}" if trial["error"] else "")


def run_all(seeds, env, repeats):
    """Run every seed `repeats` times, printing one line per trial."""
    trials = []
    for seed in seeds:
        for n in range(1, repeats + 1):
            trial = run_trial(seed, env)
            trial["trial"] = n
            trials.append(trial)
            print(format_trial_line(trial))
    return trials


def summarize(trials, env_name, repeats):
    completed = [t for t in trials if t["status"] == "ok"]
    wins = sum(t["attack_success"] for t in completed)
    return {"environment": env_name, "repeats": repeats, "trials": len(trials),
            "completed": len(completed), "attack_successes": wins,
            "attack_success_rate": wins / len(completed) if completed else None}


def write_results(output_dir, summary, trials):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    path.write_text(json.dumps({"summary": summary, "trials": trials}, indent=2), encoding="utf-8")
    return path


def print_summary(summary, results_path):
    rate = summary["attack_success_rate"]
    print(f"Attack success rate: {'N/A' if rate is None else f'{rate:.0%}'} "
          f"({summary['attack_successes']}/{summary['completed']} completed trials)")
    print(f"Results: {results_path}")


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        seeds = load_seeds(args.seeds)
        env = load_environment(args.env)
    except (OSError, ValueError, ImportError) as exc:
        parser.error(str(exc))

    try:
        trials = run_all(seeds, env, args.repeats)
    except NotImplementedError as exc:
        print(f"Cannot run: {exc}\nImplement it, or try the demo with --env mock_environment.",
              file=sys.stderr)
        return 2
    summary = summarize(trials, args.env, args.repeats)
    print_summary(summary, write_results(args.output_dir, summary, trials))
    return 1 if summary["completed"] < summary["trials"] else 0


if __name__ == "__main__":
    sys.exit(main())
