#!/bin/bash
set -e

# Repository directory path (can be customized)
REPO=${1:-/var/www/repo/fedora}

echo "=== Setting up Fedora Repository ==="
echo "Target directory: $REPO"

# Create target directory
mkdir -p "$REPO"

# Check if createrepo_c or createrepo is installed
CREATEREPO_CMD=""
if command -v createrepo_c &> /dev/null; then
  CREATEREPO_CMD="createrepo_c"
elif command -v createrepo &> /dev/null; then
  CREATEREPO_CMD="createrepo"
else
  echo "Warning: 'createrepo_c' or 'createrepo' is not installed."
  echo "Please install it using your package manager:"
  echo "  - Fedora/RHEL: sudo dnf install createrepo_c"
  echo "  - Ubuntu/Debian: sudo apt install createrepo"
  echo ""
  echo "Initializing directory structure anyway. You'll need to run createrepo manually once installed."
fi

if [ -n "$CREATEREPO_CMD" ]; then
  echo "Initializing Fedora repository with $CREATEREPO_CMD..."
  $CREATEREPO_CMD "$REPO"
fi

echo "==========================================="
echo "Fedora repository structure is ready!"
echo "You can now run ./add-package-fedora.sh to add your first package."
echo "==========================================="
