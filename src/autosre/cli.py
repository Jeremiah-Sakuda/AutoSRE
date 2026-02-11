"""CLI entry point for AutoSRE."""

import argparse
import sys

from autosre.models import IncidentType
from autosre.workflow import run_demo, run_once


def main() -> int:
    parser = argparse.ArgumentParser(description="AutoSRE — Self-Healing Cloud Operations Agent")
    parser.add_argument("--demo", action="store_true", help="Run deterministic demo scenario")
    parser.add_argument(
        "--incident-type",
        choices=[t.value for t in IncidentType],
        default=IncidentType.LATENCY_SPIKE.value,
        help="Incident type for single run (default: latency_spike)",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    args = parser.parse_args()

    if args.demo:
        ok = run_demo()
        return 0 if ok else 1
    incident_type = IncidentType(args.incident_type)
    ok = run_once(incident_type=incident_type)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
