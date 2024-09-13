#!/bin/bash

# Single .sh file to install Google Coral requirements for the Raspberry Pi
# Adapted to install specific versions of libedgetpu, tflite_runtime, and pycoral

# Update and upgrade existing packages
sudo apt-get update
sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y wget

# Step 1: Download and install libedgetpu version 16.0TF2.17.0-1
echo "Downloading libedgetpu version 16.0TF2.17.0-1..."
wget https://github.com/feranick/libedgetpu/releases/download/16.0TF2.17.0-1/libedgetpu1-16.0TF2.17.0-1_arm64.deb

echo "Installing libedgetpu..."
sudo dpkg -i libedgetpu1-16.0TF2.17.0-1_arm64.deb

# Fix any missing dependencies
sudo apt-get install -f -y

# Step 2: Download and install tflite_runtime version 2.17.0
echo "Downloading tflite_runtime version 2.17.0..."
wget https://github.com/feranick/TFlite-builds/releases/download/v2.17.0/tflite_runtime-2.17.0-cp39-cp39-linux_aarch64.whl

echo "Installing tflite_runtime..."
sudo pip3 install tflite_runtime-2.17.0-cp39-cp39-linux_aarch64.whl

# Step 3: Uninstall existing pycoral
echo "Uninstalling existing pycoral..."
sudo pip3 uninstall -y pycoral

# Step 4: Download and install pycoral version 2.0.2
echo "Downloading pycoral version 2.0.2..."
wget https://github.com/google-coral/pycoral/releases/download/v2.0.2/pycoral-2.0.2-cp39-cp39-linux_aarch64.whl

echo "Installing pycoral..."
sudo pip3 install pycoral-2.0.2-cp39-cp39-linux_aarch64.whl

# Check if Google Coral is installed
while true; do
  # Ask user to plug in USB device
  echo "Please connect the Google-Coral USB device to the USB 3.0 port. Press [y] then enter to continue."
  read -r -p "Continue? [y/N] " response
  if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]
  then
      break
  else
      echo "Invalid response. Please try again."
  fi
done

# Link the installed packages to the 'owl' virtual environment
echo "Linking pycoral and tflite_runtime to the virtual environment..."

# Specify the path to your 'owl' virtual environment
OWL_VENV_PATH="/path/to/your/owl/venv"  # Replace with the actual path

# Find the site-packages directory of the 'owl' virtual environment
OWL_SITE_PACKAGES="$OWL_VENV_PATH/lib/python3.9/site-packages"

# Copy the installed packages to the virtual environment
sudo cp -r /usr/local/lib/python3.9/dist-packages/pycoral* "$OWL_SITE_PACKAGES"
sudo cp -r /usr/local/lib/python3.9/dist-packages/tflite_runtime* "$OWL_SITE_PACKAGES"

echo "Installation completed successfully!"
