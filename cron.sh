#!/bin/sh

ROOT="$(dirname "$(readlink "${0}" || echo "${0}")")"
cd "${ROOT}"
. ENV/bin/activate
./covid19.py
