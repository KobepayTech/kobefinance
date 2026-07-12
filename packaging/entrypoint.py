"""Frozen-app entry point for PyInstaller (calls the CLI main)."""

from kobefinance.app import main

if __name__ == "__main__":
    raise SystemExit(main())
