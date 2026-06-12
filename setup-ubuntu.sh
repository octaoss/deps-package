#!/bin/bash
set -e

# Repository directory path (can be customized)
REPO=${1:-/var/www/repo/debian}

echo "=== Setting up Ubuntu/Debian Repository ==="
echo "Target directory: $REPO"

# Create required directories
mkdir -p "$REPO/pool/main"
mkdir -p "$REPO/dists/stable/main/binary-amd64"
mkdir -p "$REPO/conf"

# Create release.conf if it does not exist
if [ ! -f "$REPO/conf/release.conf" ]; then
  cat <<EOF > "$REPO/conf/release.conf"
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

# Create dummy Packages file if not exists to avoid empty listing errors
touch "$REPO/dists/stable/main/binary-amd64/Packages"

echo "==========================================="
echo "Ubuntu/Debian repository structure is ready!"
echo "You can now run ./add-package-ubuntu.sh to add your first package."
echo "==========================================="
