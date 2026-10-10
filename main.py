import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import run_cli


if __name__ == "__main__":
    exit_code = run_cli()
    sys.exit(exit_code)
