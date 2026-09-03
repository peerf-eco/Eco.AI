#!/bin/sh
# Customer image entrypoint: fix mount ownership, then exec the harness.
set -e

# Bind-mounted /data (ECO_HOME) and /project (user project) may arrive
# root-owned; make them writable by the runtime user when we start as root.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /data /project
    chown -R eco:eco /data 2>/dev/null || true
    # The project dir stays host-owned (git operations must see the real
    # ownership); only ensure the dir exists.
    exec gosu eco "$@"
fi

exec "$@"
