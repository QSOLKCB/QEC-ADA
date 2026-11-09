#!/bin/sh
# SPDX-License-Identifier: MPL-2.0
# Separate from the runtime build: prove only spark/qec_field_proofs.ad[sb].
set -eu

if ! command -v gnatprove >/dev/null 2>&1; then
  echo "NOT_RUN: GNATprove unavailable. Install a compatible Ada/SPARK toolchain." >&2
  exit 2
fi

gnatprove --version
gnatprove -P spark/qec_field.gpr -u qec_field_proofs.adb \
  --mode=all --level=2 --report=all --checks-as-errors=on \
  --warnings=error --output=oneline -f
