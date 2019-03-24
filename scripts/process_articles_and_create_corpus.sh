#!/bin/bash

source /home/xpancik2/masters-thesis-venv/bin/activate
cd /home/xpancik2/masters-thesis/
export PYTHONPATH=/home/xpancik2/masters-thesis/
export PYTHON_ENV=production
python scripts/process_articles.py
python scripts/watchdog.py
python scripts/create_preverticals.py
python scripts/create_corpus.py
