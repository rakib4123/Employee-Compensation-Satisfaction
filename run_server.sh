#!/usr/bin/env bash
# Local development server.
#
# DJANGO_DEBUG=1 is required: settings.py defaults DEBUG off, so without it
# Django refuses to start rather than fall back to the SECRET_KEY committed in
# this repository. Never set this on a deployed host.
set -euo pipefail
source venv/bin/activate
export DJANGO_DEBUG=1
python3 manage.py migrate
python3 manage.py runserver 8000
