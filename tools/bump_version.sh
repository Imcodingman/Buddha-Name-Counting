#!/bin/sh
# Stamp a new cache-busting version into index.html (app.js passes it on to the data files)
# and version.txt (which open pages poll to reload themselves onto the new version).
# Run before each release:  sh tools/bump_version.sh
cd "$(dirname "$0")/.." && v=$(date +%Y%m%d%H%M) && sed -i -E "s/\?v=[0-9]+/?v=$v/g" index.html && echo "$v" > version.txt && echo "version $v"
