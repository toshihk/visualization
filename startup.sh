#!/bin/bash
set -e

cd /home/site/wwwroot
export PYTHONPATH="/home/site/wwwroot/.python_packages/lib/site-packages:${PYTHONPATH}"

python -m gunicorn --bind "0.0.0.0:${PORT:-8000}" --timeout 600 app.main:server
