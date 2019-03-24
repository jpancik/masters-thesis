#!/bin/bash

source /home/xpancik2/masters-thesis-venv/bin/activate
cd /home/xpancik2/masters-thesis/
export PYTHONPATH=/home/xpancik2/masters-thesis/
export PYTHON_ENV=production
python scripts/gather_articles_metadata.py
python scripts/download_articles.py
