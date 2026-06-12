#!/bin/bash
set -e

REPO=${1:-/var/www/repo/debian}

echo "=== Checking and installing dependencies ==="
DEPS_TO_INSTALL=()

if ! command -v apt-ftparchive &>/dev/null; then
  if command -v apt-get &>/dev/null; then
    DEPS_TO_INSTALL+=("apt-utils")
  else
    echo "Warning: apt-ftparchive is missing and this system is not Debian/Ubuntu-based."
    echo "Please install apt-ftparchive manually."
  fi
fi

if ! command -v wget &>/dev/null; then
  DEPS_TO_INSTALL+=("wget")
fi

if [ ${#DEPS_TO_INSTALL[@]} -ne 0 ]; then
  echo "Installing required packages: ${DEPS_TO_INSTALL[*]}"
  if command -v apt-get &>/dev/null; then
    sudo apt-get update && sudo apt-get install -y "${DEPS_TO_INSTALL[@]}"
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y "${DEPS_TO_INSTALL[@]}"
  elif command -v yum &>/dev/null; then
    sudo yum install -y "${DEPS_TO_INSTALL[@]}"
  else
    echo "Could not detect package manager to install: ${DEPS_TO_INSTALL[*]}"
    echo "Please install them manually."
  fi
else
  echo "All dependencies (apt-ftparchive, wget) are already installed."
fi

echo "=== Setting up Ubuntu/Debian Repository ==="

echo "Target directory: $REPO"

mkdir -p "$REPO/pool/main"
mkdir -p "$REPO/dists/stable/main/binary-amd64"
mkdir -p "$REPO/conf"

if [ ! -f "$REPO/conf/release.conf" ]; then
  cat <<EOF >"$REPO/conf/release.conf"
APT::FTPArchive::Release::Origin "Custom Linux Repository";
APT::FTPArchive::Release::Label "Custom Linux Repository";
APT::FTPArchive::Release::Suite "stable";
APT::FTPArchive::Release::Codename "stable";
APT::FTPArchive::Release::Architectures "amd64";
APT::FTPArchive::Release::Components "main";
APT::FTPArchive::Release::Description "Repository for custom Debian/Ubuntu packages";
EOF
  echo "Created configuration file: $REPO/conf/release.conf"
else
  echo "Configuration file already exists: $REPO/conf/release.conf"
fi

touch "$REPO/dists/stable/main/binary-amd64/Packages"

echo "==========================================="
echo "Ubuntu/Debian repository structure is ready!"
echo "You can now run ./add-package-ubuntu.sh to add your first package."
echo "==========================================="
