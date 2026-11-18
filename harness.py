"""Run a JSON email control and record the agent reply."""

import argparse
import json
import sys
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

def build_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--control", type=Path, required=True,
                        help="JSON fixture for a read-only control trial")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo-control", action="store_true",
                        help="use the deterministic fake agent for the control")
    mode.add_argument("--openai-model", metavar="MODEL_ID",
                      help="run the control with an OpenAI model through LangChain")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent / "results")
    return parser


def write_results(output_dir, summary, trials):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    path.write_text(json.dumps({"summary": summary, "trials": trials}, indent=2), encoding="utf-8")
    return path


def run_control(path, repeats, output_dir, *, agent, env_name, model_id=None):
    """Run the JSON-only control and store each final reply in the standard report."""
    from environment import invoke_json_agent

    fixture = json.loads(path.read_text(encoding="utf-8"))
    expected = fixture["expected_result"]
    if agent is None:
        raise NotImplementedError("No JSON agent configured. Use --demo-control for the fake agent.")
    trials = []
    for number in range(1, repeats + 1):
        response, error = "", ""
        started = time.perf_counter()
        try:
            # A fresh copy prevents an agent from changing the next trial's input.
            response = invoke_json_agent(fixture["user_task"], deepcopy(fixture["emails"]),
                                         agent=agent)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        checks = {}
        if not error:
            # Phrase checks verify the deterministic demo. Semantic scoring can come later.
            normalized = " ".join(response.casefold().split())
            checks = {
                "required_facts": all(" ".join(fact.casefold().split()) in normalized
                                      for fact in expected["required_facts"]),
                "excluded_facts": all(" ".join(fact.casefold().split()) not in normalized
                                      for fact in expected["excluded_facts"]),
            }
        passed = all(checks.values()) if not error else None
        trials.append({"seed": fixture["name"], "trial": number,
                       "status": "error" if error else "ok", "error": error,
                       "elapsed_seconds": round(time.perf_counter() - started, 4),
                       "response": response, "checks": checks, "control_passed": passed})

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


def main():
    from environment import build_openai_control_agent, demo_unread_summary

    parser = build_parser()
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be at least 1")

    # Reuse the same callable across trials. The agent owns any conversation state.
    agent = demo_unread_summary if args.demo_control else None
    env_name = "demo_control" if args.demo_control else "environment"
    try:
        if args.openai_model:
            agent = build_openai_control_agent(args.openai_model)
            env_name = "openai"
        return run_control(args.control, args.repeats, args.output_dir,
                           agent=agent, env_name=env_name, model_id=args.openai_model)
    except NotImplementedError as exc:
        print(f"Cannot run: {exc}", file=sys.stderr)
        return 2
    except ImportError:
        parser.error("install the OpenAI control dependencies with python -m pip install -r requirements.txt")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
