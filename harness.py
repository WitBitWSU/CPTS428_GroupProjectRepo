"""Run a JSON email control and record the agent reply."""

import argparse
import json
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from email_tools import capture_tool_calls


CONTROLS_DIR = Path(__file__).resolve().parent / "controls"


def build_parser():
    """Define the CLI and make the demo and provider modes mutually exclusive."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    fixtures = parser.add_mutually_exclusive_group(required=True)
    fixtures.add_argument("--control", type=Path, help="JSON fixture for a control trial")
    fixtures.add_argument("--all-controls", action="store_true",
                          help="run every JSON fixture in controls/ with an OpenAI model")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo-control", action="store_true",
                      help="use the deterministic fake agent for the control")
    mode.add_argument("--demo-send-control", action="store_true",
                      help="verify an approved send in the in-memory simulator")
    mode.add_argument("--openai-model", metavar="MODEL_ID",
                      help="run the control with an OpenAI model through LangChain")
    mode.add_argument("--openai-send-control", metavar="MODEL_ID",
                      help="let an OpenAI model call the approved send tool")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results")
    return parser


def write_results(output_dir, summary, trials):
    """Write one timestamped JSON report for the entire run."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    path.write_text(json.dumps({"summary": summary, "trials": trials}, indent=2), encoding="utf-8")
    return path


def run_control(path, repeats, output_dir, *, agent, env_name, model_id=None):
    """Run and score each trial, then return an exit code for the whole run."""
    fixture = json.loads(path.read_text(encoding="utf-8"))
    expected = fixture["expected_result"]
    if agent is None:
        raise NotImplementedError("No JSON agent configured. Use --demo-control for the fake agent.")
    trials = []
    for number in range(1, repeats + 1):
        response, error = "", ""
        started = time.perf_counter()
        with capture_tool_calls() as tool_calls:
            try:
                # A fresh copy prevents an agent from changing the next trial's input.
                reply = agent(fixture["user_task"], deepcopy(fixture["emails"]))
                if not isinstance(reply, str):
                    raise TypeError("The JSON agent must return its final reply as text")
                response = reply
            except Exception as exc:
                # Keep the trace and continue running the remaining trials.
                error = f"{type(exc).__name__}: {exc}"

        checks = {}
        if not error:
            # Use case-insensitive substring checks with normalized whitespace.
            normalized = " ".join(response.casefold().split())
            checks = {
                "required_facts": all(" ".join(fact.casefold().split()) in normalized
                                      for fact in expected["required_facts"]),
                "excluded_facts": all(" ".join(fact.casefold().split()) not in normalized
                                      for fact in expected["excluded_facts"]),
            }
            if "required_tools" in expected:
                completed_tools = {call["tool"] for call in tool_calls
                                   if call["outcome"] == "completed"}
                checks["required_tools"] = completed_tools.issuperset(expected["required_tools"])
        passed = all(checks.values()) if not error else None
        trials.append({"seed": fixture["name"], "trial": number,
                       "status": "error" if error else "ok", "error": error,
                       "elapsed_seconds": round(time.perf_counter() - started, 4),
                       "response": response, "tool_calls": tool_calls,
                       "checks": checks, "control_passed": passed})

    passed_count = sum(trial["control_passed"] is True for trial in trials)
    summary = {"environment": env_name,
               "repeats": repeats, "trials": len(trials),
               "completed": sum(trial["status"] == "ok" for trial in trials),
               "control_passes": passed_count}
    if model_id is not None:
        summary["requested_model"] = model_id
    print(f"Control passed: {passed_count}/{len(trials)}")
    print(f"Results: {write_results(output_dir, summary, trials)}")
    return 0 if passed_count == len(trials) else 1


def run_all_controls(repeats, output_dir, model_id):
    """Run each repository control and keep its report in a separate directory."""
    from environment import build_openai_control_agent

    paths = sorted(CONTROLS_DIR.glob("*.json"))
    if not paths:
        raise ValueError(f"No JSON control fixtures found in {CONTROLS_DIR}")

    summary_agent = build_openai_control_agent(model_id)
    send_agent = build_openai_control_agent(model_id, send_control=True)
    statuses = []
    for path in paths:
        # Only the built-in send control uses the fixed, approved outgoing draft.
        is_send = path.name == "simulated_send.json"
        print(f"Running {path.name}")
        try:
            status = run_control(
                path, repeats, output_dir / path.stem,
                agent=send_agent if is_send else summary_agent,
                env_name="openai_send_control" if is_send else "openai",
                model_id=model_id,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            print(f"Could not run {path.name}: {exc}", file=sys.stderr)
            status = 2
        statuses.append(status)

    print(f"Control fixtures passed: {statuses.count(0)}/{len(paths)}")
    return max(statuses)


def main():
    """Select an agent from the CLI options and run the requested fixture."""
    from environment import build_openai_control_agent, demo_simulated_send, demo_unread_summary

    parser = build_parser()
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.all_controls and not args.openai_model:
        parser.error("--all-controls requires --openai-model MODEL_ID")

    # Reuse the same callable across trials. The agent owns any conversation state.
    agent = demo_unread_summary if args.demo_control else None
    env_name = "demo_control" if args.demo_control else "environment"
    model_id = args.openai_send_control or args.openai_model
    try:
        if args.all_controls:
            return run_all_controls(args.repeats, args.output_dir, model_id)
        if model_id:
            send_control = args.openai_send_control is not None
            agent = build_openai_control_agent(model_id, send_control=send_control)
            env_name = "openai_send_control" if send_control else "openai"
        elif args.demo_send_control:
            agent = demo_simulated_send
            env_name = "demo_send_control"
        return run_control(args.control, args.repeats, args.output_dir,
                           agent=agent, env_name=env_name, model_id=model_id)
    except NotImplementedError as exc:
        print(f"Cannot run: {exc}", file=sys.stderr)
        return 2
    except ImportError:
        parser.error("install the OpenAI control dependencies with python -m pip install -r requirements.txt")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
