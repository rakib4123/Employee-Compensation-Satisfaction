"""Local development bootstrap: install dependencies, migrate, serve.

DJANGO_DEBUG=1 is set below because settings.py defaults DEBUG off. Without
it Django refuses to start rather than silently fall back to the SECRET_KEY
committed in this repository. Never set it on a deployed host — Render should
supply SECRET_KEY and leave DJANGO_DEBUG unset.
"""

import os
import subprocess

ENV = {**os.environ, "DJANGO_DEBUG": "1"}


def main():
    print("Installing requirements...")
    subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)
    print("Applying migrations...")
    subprocess.run(["venv/bin/python", "manage.py", "migrate"], check=True, env=ENV)
    print("Starting server on http://127.0.0.1:8000 ...")
    subprocess.run(["venv/bin/python", "manage.py", "runserver", "8000"], env=ENV)


if __name__ == "__main__":
    main()
