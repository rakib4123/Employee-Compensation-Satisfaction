import os
import subprocess

def main():
    print("Installing requirements...")
    subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)
    print("Starting migrations...")
    subprocess.run(["venv/bin/python", "manage.py", "migrate"], check=True)
    print("Starting server...")
    subprocess.run(["venv/bin/python", "manage.py", "runserver", "8000"])

if __name__ == "__main__":
    main()
