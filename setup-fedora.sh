#!/bin/bash
set -e

REPO_URL="https://deps.oktanio.dev"
REPO=${1:-/var/www/repo/fedora}

echo "=== Checking and installing dependencies ==="
DEPS_TO_INSTALL=()
CREATEREPO_PKG=""

if ! command -v createrepo_c &> /dev/null && ! command -v createrepo &> /dev/null; then
  if command -v dnf &> /dev/null || command -v yum &> /dev/null; then
    CREATEREPO_PKG="createrepo_c"
  elif command -v apt-get &> /dev/null; then
    CREATEREPO_PKG="createrepo"
  else
    echo "Warning: Neither createrepo_c nor createrepo is installed, and package manager is unknown."
  fi
fi

if [ -n "$CREATEREPO_PKG" ]; then
  DEPS_TO_INSTALL+=("$CREATEREPO_PKG")
fi

if ! command -v wget &> /dev/null; then
  DEPS_TO_INSTALL+=("wget")
fi

if [ ${#DEPS_TO_INSTALL[@]} -ne 0 ]; then
  echo "Installing required packages: ${DEPS_TO_INSTALL[*]}"
  if command -v dnf &> /dev/null; then
    sudo dnf install -y "${DEPS_TO_INSTALL[@]}"
  elif command -v yum &> /dev/null; then
    sudo yum install -y "${DEPS_TO_INSTALL[@]}"
  elif command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get install -y "${DEPS_TO_INSTALL[@]}"
  else
    echo "Could not detect package manager to install: ${DEPS_TO_INSTALL[*]}"
    echo "Please install them manually."
  fi
else
  echo "All dependencies (createrepo, wget) are already installed."
fi


CREATEREPO_CMD=""
if command -v createrepo_c &> /dev/null; then
  CREATEREPO_CMD="createrepo_c"
elif command -v createrepo &> /dev/null; then
  CREATEREPO_CMD="createrepo"
fi

echo "=== Setting up Fedora Repository ==="
echo "Target directory: $REPO"


mkdir -p "$REPO"

cat <<EOF > "$REPO/deps-oktanio.repo"
[deps-oktanio]
name=Deps Oktanio Repository
baseurl=$REPO_URL/fedora
enabled=1
gpgcheck=0
EOF

if [ -n "$CREATEREPO_CMD" ]; then
  echo "Initializing Fedora repository with $CREATEREPO_CMD..."
  $CREATEREPO_CMD "$REPO"
fi

echo "==========================================="
echo "Fedora repository structure is ready!"
echo "A client configuration file has been created at $REPO/deps-oktanio.repo"
echo "You can now run ./add-package-fedora.sh to add your first package."
echo "==========================================="

