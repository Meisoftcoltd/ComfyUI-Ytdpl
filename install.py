import os
import sys
import subprocess

def install_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        print(f"Installing requirements from {requirements_path}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            print("Successfully installed requirements.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing requirements: {e}")
    else:
        print("No requirements.txt found.")

if __name__ == "__main__":
    install_requirements()
