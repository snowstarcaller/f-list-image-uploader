#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First run: setting things up, this takes a minute..."
  python3 -m venv .venv || { echo "Python isn't installed. Get it from https://www.python.org/downloads/"; read -p "Press Enter to close"; exit 1; }
fi
.venv/bin/python -m pip install -q --disable-pip-version-check playwright pillow
.venv/bin/python flist_uploader.py
