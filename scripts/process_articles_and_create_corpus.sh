#!/bin/bash

source /home/xpancik2/masters-thesis-venv/bin/activate
cd /home/xpancik2/masters-thesis/
export PYTHONPATH=/home/xpancik2/masters-thesis/
export PYTHON_ENV=production
python scripts/process_articles.py
python scripts/watchdog.py
python scripts/create_preverticals.py
python scripts/create_corpus.py
scripts/compile_subcorpuses.sh
python scripts/do_analysis.py --type all
rm /nlp/projekty/webtrack/public_html/*
python scripts/generate_html.py --output /nlp/projekty/webtrack/public_html/
cat files/compiled_corpora_email.txt | mail -s "Dezinfo corpora compiled" 139654@mail.muni.cz