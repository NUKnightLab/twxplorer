#!/bin/bash
#
# run daily, cron it up as:
#
# /home/apps/sites/twxplorer/clean-prd.sh >> /home/apps/log/twxplorer/clean.log 2>&1

echo "[`date`] Starting clean"
 
source /home/apps/env/twxplorer/bin/activate

cd /home/apps/sites/twxplorer

export FLASK_SETTINGS_MODULE='core.settings.prd'

python -u clean.py --days=7

echo "[`date`] Ending clean"

