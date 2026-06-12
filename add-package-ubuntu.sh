#!/bin/bash
set -e

REPO=/var/www/repo/debian

mkdir -p "$REPO/pool/main"

URL="$1"

wget -N -P "$REPO/pool/main" "$URL"

cd "$REPO"

apt-ftparchive packages pool >dists/stable/main/binary-amd64/Packages
gzip -kf dists/stable/main/binary-amd64/Packages

apt-ftparchive \
  -c conf/release.conf \
  release dists/stable >dists/stable/Release
