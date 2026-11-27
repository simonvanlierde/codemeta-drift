#!/usr/bin/env bash
set -euo pipefail

out=${1:?pass the export directory}
mkdir -- "$out"
for curated in src/codemeta_drift/curated-*.json; do
  tag=${curated##*/curated-}
  cp -- "examples/mapping-$tag" "$out/"
done
cd -- "$out"
sha256sum mapping-*.json >SHA256SUMS
