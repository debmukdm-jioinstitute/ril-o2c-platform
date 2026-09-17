#!/usr/bin/env bash
# XGBoost and LightGBM's macOS wheels link against libomp.dylib via Homebrew's install path
# (/opt/homebrew/opt/libomp/lib) but do not bundle it. The normal fix is `brew install libomp`.
# This script is a fallback for machines without Homebrew or admin rights: it pulls the
# equivalent library straight from conda-forge and patches the two extension dylibs to also
# search this project's venv for it, via install_name_tool -add_rpath (no sudo, no system
# changes — everything lands inside .venv/).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .venv/native-libs/libomp.dylib ]; then
  echo "libomp.dylib already present at .venv/native-libs/ — nothing to do."
  exit 0
fi

if ! python3 -c "import zstandard" 2>/dev/null; then
  pip install --only-binary=:all: zstandard -q
fi

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

PKG_URL="https://conda.anaconda.org/conda-forge/osx-arm64/llvm-openmp-23.1.1-hdb3d66b_0.conda"
curl -sL -o "$WORKDIR/pkg.conda" "$PKG_URL"
(cd "$WORKDIR" && unzip -oq pkg.conda)

python3 - "$WORKDIR" <<'PY'
import sys, tarfile, zstandard, glob
workdir = sys.argv[1]
tar_path = glob.glob(f"{workdir}/pkg-llvm-openmp-*.tar.zst")[0]
dctx = zstandard.ZstdDecompressor()
with open(tar_path, "rb") as f:
    with tarfile.open(fileobj=dctx.stream_reader(f), mode="r|") as tar:
        tar.extractall(f"{workdir}/out")
PY

mkdir -p .venv/native-libs
cp "$WORKDIR/out/lib/libomp.dylib" .venv/native-libs/libomp.dylib

NATIVE_DIR="$PWD/.venv/native-libs"
for lib in $(find .venv -iname "libxgboost.dylib" -o -iname "lib_lightgbm.dylib"); do
  if ! otool -l "$lib" | grep -q "$NATIVE_DIR"; then
    install_name_tool -add_rpath "$NATIVE_DIR" "$lib"
    echo "Patched rpath: $lib"
  fi
done

echo "Done. Verify with: python3 -c 'import xgboost, lightgbm'"
