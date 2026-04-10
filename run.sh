#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
cd proyecto/src
python main_tk.py
