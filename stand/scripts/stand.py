#!/usr/bin/env python3
"""Stand engine: the only program that writes your Stand files. Use the /stand:* skills."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    from engine.cli import main
    sys.exit(main())
