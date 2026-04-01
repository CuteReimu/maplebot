#!/usr/bin/env bash
if command -v python3 &>/dev/null; then
  PYTHON=python3
else
  PYTHON=python
fi
ENVIRONMENT=dev "$PYTHON" bot.py