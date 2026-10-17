#!/usr/bin/env python3
"""tovar engine: the only program that writes your tovar files. Use the /tovar-core:* skills."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    from engine.cli import main
    sys.exit(main())
