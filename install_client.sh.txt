#!/bin/bash

TARGET_DIR="/opt/terminal_client"
FORM_DIR="$TARGET_DIR/forms"
DESKTOP_FILE="/usr/share/applications/terminal_client.desktop"
DESKTOP_USER="$HOME/Desktop/terminal_client.desktop"
APP_NAME="terminal_client.py"
SOURCE_DIR="$(dirname "$(realpath "$0")")"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo $0)"
    exit 1
fi

# Dependency Check and Install Section
echo "Checking and installing dependencies..."

# Ensure Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found. Installing..."
    apt update || { echo "Failed to update package list"; exit 1; }
    apt install -y python3 || { echo "Failed to install Python 3"; exit 1; }
else
    echo "Python 3 already installed."
fi

# Check and install python3-pip for package management
if ! command -v pip3 &> /dev/null; then
    echo "pip3 not found. Installing..."
    apt install -y python3-pip || { echo "Failed to install pip3"; exit 1; }
else
    echo "pip3 already installed."
fi

# Check and install libncurses5 for curses module  # CHANGE: Added for terminal_client.py v4.3.5 curses dependency
if ! dpkg -l | grep -q libncurses5; then
    echo "libncurses5 not found. Installing..."
    apt install -y libncurses5 || { echo "Failed to install libncurses5"; exit 1; }
else
    echo "libncurses5 already installed."
fi

# List of required Python packages  # CHANGE: Added crcmod for v4.3.5 AX.25 support
PYTHON_PACKAGES=("pandas" "tabulate" "crcmod")

# Check and install each Python package
for pkg in "${PYTHON_PACKAGES[@]}"; do
    if ! python3 -c "import $pkg" 2> /dev/null; then
        echo "Installing $pkg..."
        pip3 install "$pkg" || { echo "Failed to install $pkg"; exit 1; }
    else
        echo "$pkg already installed."
    fi
done

# Verify all Python packages are installed  # CHANGE: Added verification step
echo "Verifying Python package installations..."
for pkg in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import $pkg" 2> /dev/null; then
        echo "$pkg verified."
    else
        echo "Error: $pkg failed to install correctly."
        exit 1
    fi
done

# Copy installer and app to home (unchanged)
cp "$SOURCE_DIR/install_client.sh" "$HOME/" || { echo "Failed to copy install_client.sh"; exit 1; }
cp "$SOURCE_DIR/$APP_NAME" "$HOME/" || { echo "Failed to copy $APP_NAME"; exit 1; }
chmod +x "$HOME/install_client.sh"

# Set up directories (unchanged)
mkdir -p "$TARGET_DIR" "$FORM_DIR"
chgrp users "$TARGET_DIR" "$FORM_DIR"
chmod 775 "$TARGET_DIR" "$FORM_DIR"

# Copy app to target (unchanged)
if [ -f "$HOME/$APP_NAME" ]; then
    cp "$HOME/$APP_NAME" "$TARGET_DIR/"
    chmod 775 "$TARGET_DIR/$APP_NAME"
    chgrp users "$TARGET_DIR/$APP_NAME"
else
    echo "Error: $APP_NAME not found in $HOME"
    exit 1
fi

# Initialize people.csv (unchanged)
PEOPLE_FILE="$TARGET_DIR/people.csv"
if [ ! -f "$PEOPLE_FILE" ]; then
    echo "id,name" > "$PEOPLE_FILE"
    echo "1,John Doe" >> "$PEOPLE_FILE"
    echo "2,Jane Smith" >> "$PEOPLE_FILE"
fi
chmod 664 "$PEOPLE_FILE"
chgrp users "$PEOPLE_FILE"

# Create desktop file (unchanged)
cat << EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=Terminal Client
Exec=/usr/bin/python3 $TARGET_DIR/$APP_NAME
Type=Application
Terminal=true
Icon=utilities-terminal
Categories=Utility;
EOF
chmod 644 "$DESKTOP_FILE"

# Copy to user desktop if exists (unchanged)
if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$DESKTOP_USER"
    chmod 644 "$DESKTOP_USER"
    echo "You may need to right-click the desktop icon and select 'Trust' to enable it."
fi

echo "Installation complete!"
echo "App installed to $TARGET_DIR"
echo "Run with: python3 $TARGET_DIR/$APP_NAME"