"""Runtime self-test — the Bootstrap Gate.

    python runtime/self_test.py

The runtime may be created by an agent, but it may never declare itself
correct. This suite is the machine evidence. Exit code 0 = VERIFIED.

Gate implementations live in the ``gates`` package (grouped by concern);
this file is only the CLI entry point.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gates  # noqa: E402


def main():
    if not gates.run_all():
        sys.exit(1)


if __name__ == "__main__":
    main()
