#!/bin/sh

ROOT="$(dirname "$(readlink "${0}" || echo "${0}")")"
cd "${ROOT}"
. env/bin/activate
./covid19.py
