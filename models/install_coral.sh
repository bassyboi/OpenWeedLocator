#!/bin/bash

# Single .sh file to install Hailo AI requirements for the Raspberry Pi
# Adapted from Hailo installation instructions with assistance from ChatGPT

# Update and upgrade existing packages
sudo apt-get update
sudo apt-get upgrade -y

# Variables
SDK_INSTALLER="hailo-sdk-4.15.0-1.deb"  # Replace with the correct version
SDK_DOWNLOAD_URL="https://hailo.ai/downloads/$SDK_INSTALLER"  # Replace with the correct URL
VENV_NAME="owl"  # Replace with your virtual environment name

# Download Hailo SDK if not already downloaded
if [ ! -f "$SDK_INSTALLER" ]; then
    echo "Downloading Hailo SDK installer..."
    wget "$SDK_DOWNLOAD_URL" -O "$SDK_INSTALLER"
else
    echo "Hailo SDK installer already downloaded. Skipping download."
fi

# Install prerequisites
sudo apt-get install -y python3-pip python3-venv python3-dev libopencv-dev python3-opencv

# Install Hailo SDK
sudo dpkg -i "$SDK_INSTALLER" || true  # Ignore errors for missing dependencies
sudo apt-get install -f -y  # Fix missing dependencies
sudo dpkg -i "$SDK_INSTALLER"

# Source Hailo environment setup script
HAILO_SDK_PATH="/usr/local/hailo_sdk"
if [ -f "$HAILO_SDK_PATH/setup_env.sh" ]; then
    echo "Sourcing Hailo SDK environment script..."
    echo "source $HAILO_SDK_PATH/setup_env.sh" >> "$HOME/.bashrc"
    source "$HAILO_SDK_PATH/setup_env.sh"
else
    echo "Hailo SDK environment script not found. Installation may have failed."
    exit 1
fi

# Check if Hailo device is connected
while true; do
  # Ask user to plug in Hailo device
  echo "Please connect the Hailo device to the USB port. Press [y] then enter to continue."
  read -r -p "Continue? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
      # Check if device is detected
      if lsusb | grep -i "1fc9:0021" >/dev/null 2>&1; then
          echo "Hailo device detected."
          break
      else
          echo "Hailo device not detected. Please ensure it is connected properly."
      fi
  else
      echo "Invalid response. Please try again."
  fi
done

echo "Installing required Python packages in the virtual environment..."

# Install virtual environment if it doesn't exist
if [ ! -d "$HOME/$VENV_NAME" ]; then
    python3 -m venv "$HOME/$VENV_NAME"
fi

# Activate the virtual environment
source "$HOME/$VENV_NAME/bin/activate"

# Upgrade pip and install necessary Python packages
pip install --upgrade pip
pip install numpy opencv-python

# Link Hailo SDK Python packages to the virtual environment
echo "Linking Hailo SDK Python packages to the virtual environment..."

# Find the site-packages directory of the Hailo SDK
HAILO_PYTHON_DIR="$HAILO_SDK_PATH/lib/python"
HAILO_SITE_PACKAGES=$(find "$HAILO_PYTHON_DIR" -name "site-packages" -type d)

# Find the site-packages directory of the virtual environment
VENV_SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")

# Copy the Hailo SDK Python packages to the virtual environment
cp -r "$HAILO_SITE_PACKAGES/"* "$VENV_SITE_PACKAGES/"

echo "Hailo installation and setup completed successfully."

# Deactivate virtual environment
deactivate
