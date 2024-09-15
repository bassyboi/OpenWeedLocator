#!/bin/bash

# install_coral.sh
# Script to install Google Coral requirements on Raspberry Pi
# Includes repository setup, device detection, udev rules, and Python virtual environment setup

# Exit immediately if a command exits with a non-zero status
set -e

# Function to display informational messages
echo_info() {
    echo -e "\e[32m[INFO]\e[0m $1"
}

# Function to display warning messages
echo_warn() {
    echo -e "\e[33m[WARNING]\e[0m $1"
}

# Function to display error messages
echo_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

# Ensure the script is run with sudo
if [ "$EUID" -ne 0 ]; then
    echo_error "Please run as root (use sudo)."
    exit 1
fi

# Variables
CORAL_REPO_LIST="/etc/apt/sources.list.d/coral-edgetpu.list"
CORAL_KEYRING="/usr/share/keyrings/coral-edgetpu-keyring.gpg"
VENV_DIR="$HOME/coral_env"
USB_ID_VENDOR="1a6e"
USB_ID_PRODUCT="089a"

# Update and upgrade existing packages
echo_info "Updating and upgrading existing packages..."
apt-get update -y
apt-get upgrade -y

# Add Coral repository if not already added
if [ ! -f "$CORAL_REPO_LIST" ]; then
    echo_info "Adding Google Coral repository..."
    echo "deb [signed-by=$CORAL_KEYRING] https://packages.cloud.google.com/apt coral-edgetpu-stable main" | tee "$CORAL_REPO_LIST"
else
    echo_info "Google Coral repository already exists. Skipping addition."
fi

# Import the Coral GPG key using the recommended keyring method
if [ ! -f "$CORAL_KEYRING" ]; then
    echo_info "Importing Google Coral GPG key..."
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor | tee "$CORAL_KEYRING" > /dev/null
else
    echo_info "Google Coral GPG key already exists. Skipping import."
fi

# Update package lists after adding Coral repository
echo_info "Updating package lists..."
apt-get update -y

# Prompt user for operating frequency choice
echo_info "Choose operating frequency for Google Coral:"
echo "1) Standard Operating Frequency"
echo "2) MAX Operating Frequency (Increases framerate but also device temperature and power consumption)"
read -r -p "Enter choice [1/2] (default is 1): " freq_choice

# Install the selected operating frequency package
if [[ "$freq_choice" == "2" ]]; then
    echo_info "Installing MAX OPERATING FREQUENCY..."
    apt-get install -y libedgetpu1-max
else
    echo_info "Installing STANDARD OPERATING FREQUENCY..."
    apt-get install -y libedgetpu1-std
fi

# Set up Udev rules for proper permissions
echo_info "Setting up udev rules for Google Coral USB Accelerator..."
UDEV_RULES_FILE="/etc/udev/rules.d/99-edgetpu.rules"

# Check if udev rules already exist
if grep -q "$USB_ID_VENDOR:$USB_ID_PRODUCT" "$UDEV_RULES_FILE" 2>/dev/null; then
    echo_info "Udev rules already exist. Skipping creation."
else
    echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"$USB_ID_VENDOR\", ATTR{idProduct}==\"$USB_ID_PRODUCT\", MODE=\"0666\"" | tee "$UDEV_RULES_FILE" > /dev/null
    echo_info "Udev rules created."
    echo_info "Reloading udev rules..."
    udevadm control --reload-rules
    udevadm trigger
fi

# Detect the Coral USB Accelerator by its specific USB ID
detect_device() {
    if lsusb | grep -i "$USB_ID_VENDOR:$USB_ID_PRODUCT" >/dev/null 2>&1; then
        echo_info "Google Coral USB device detected."
        return 0
    else
        echo_warn "Google Coral USB device not detected. Please ensure it is connected properly."
        return 1
    fi
}

# Prompt user to confirm device connection
while true; do
    echo_info "Please connect the Google Coral USB device to a USB 3.0 port (blue ports)."
    read -r -p "Have you connected the device? [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY])
            if detect_device; then
                break
            fi
            ;;
        [nN][oO]|[nN]|'')
            echo_warn "Please connect the device to proceed."
            ;;
        *)
            echo_warn "Invalid response. Please enter y or n."
            ;;
    esac
done

# Install Python 3.9 and virtual environment tools if not already installed
echo_info "Installing Python 3.9 and virtual environment tools..."
apt-get install -y python3.9 python3.9-venv python3.9-dev

# Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo_info "Creating Python 3.9 virtual environment at $VENV_DIR..."
    sudo -u "$SUDO_USER" python3.9 -m venv "$VENV_DIR"
else
    echo_info "Virtual environment $VENV_DIR already exists. Skipping creation."
fi

# Activate the virtual environment and install pycoral
echo_info "Activating virtual environment and installing pycoral..."
sudo -u "$SUDO_USER" bash -c "source $VENV_DIR/bin/activate && pip install --upgrade pip && pip install pycoral"

# Final message with usage instructions
echo_info "Google Coral installation completed successfully."
echo_info "To activate the Coral virtual environment, run:"
echo_info "source $VENV_DIR/bin/activate"
echo_info "To deactivate, simply run:"
echo_info "deactivate"

