#!/bin/bash
set -e


REPO=/var/www/repo/fedora

if [ -z "$1" ]; then
  echo "Usage: $0 <URL_OR_PATH_TO_RPM>"
  exit 1
fi

TARGET="$1"


CREATEREPO_CMD=""
if command -v createrepo_c &> /dev/null; then
  CREATEREPO_CMD="createrepo_c"
elif command -v createrepo &> /dev/null; then
  CREATEREPO_CMD="createrepo"
else
  echo "Error: 'createrepo_c' or 'createrepo' is not installed."
  echo "Please install it using: sudo dnf install createrepo_c (Fedora/RHEL) or sudo apt install createrepo (Ubuntu/Debian)"
  exit 1
fi

mkdir -p "$REPO"


if [[ "$TARGET" =~ ^https?:// ]]; then
  echo "Downloading RPM from $TARGET..."
  wget -N -P "$REPO" "$TARGET"
else
  
  if [ -f "$TARGET" ]; then
    echo "Copying RPM from $TARGET..."
    cp -u "$TARGET" "$REPO/"
  else
    echo "Error: File or URL '$TARGET' not found."
    exit 1
  fi
fi


echo "Updating Fedora repository metadata with $CREATEREPO_CMD..."
$CREATEREPO_CMD --update "$REPO"

echo "==========================================="
echo "Package added successfully to Fedora repository!"
echo "==========================================="
