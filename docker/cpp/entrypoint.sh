#!/bin/sh
set -eu
if [ "$#" -eq 0 ]; then
  printf '%s\n' 'CTEAS-next research-scoped C++20 portable container'
  printf '%s\n' 'Available standalone programs:'
  ls -1 /opt/cteas/bin
  printf '%s\n' 'Mount inputs read-only under /cases and outputs under /results.'
  printf '%s\n' 'No generic P6/P7/G5 execution or wet deposition is certified.'
  exit 0
fi
exec "$@"
