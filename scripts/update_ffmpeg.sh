#!/bin/bash
# This file is needed to install the most recent possible version of ffmpeg,
# which we need in order to properly read webm audio files from iOS. (The most recent
# ffmpeg from the debian repositories is 4.x. We need 6.x.)
MAJ_VERSION="6"
VERSION="6.0.1-5"
DEB_FILE="jellyfin-ffmpeg${MAJ_VERSION}_${VERSION}-buster_amd64.deb"

echo "Downloading jellyfin-ffmpeg v$VERSION ($DEB_FILE)"
echo "Executing 'wget -q https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v$VERSION/$DEB_FILE'"
wget -q https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v$VERSION/$DEB_FILE
apt install -y ./$DEB_FILE

ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/local/bin/ffmpeg

apt -y autoremove

rm -f ./*.deb
rm -f /*.deb
