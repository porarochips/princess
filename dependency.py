import subprocess
import sys

def install_requirements():
    """Install required packages"""
    requirements = [
        "opencv-python==4.8.1.78",
        "mediapipe==0.10.7", 
        "numpy==1.24.3",
        "pycaw==20230407",
        "comtypes==1.2.0"
    ]
    
    print("Installing required packages...")
    
    for package in requirements:
        try:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
    
    print("\nInstallation complete!")
    print("You can now run the hand volume control script.")

if __name__ == "__main__":
    install_requirements()

