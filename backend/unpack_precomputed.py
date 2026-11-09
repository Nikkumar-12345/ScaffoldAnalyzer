"""
Unpacks the precomputed caches during the Docker image build.

This is only a speed-up. Each service (PrecomputedService,
HomologService) unpacks its own .gz on first use if the plain .db is
not there, so a failure here costs a few seconds at start-up and
nothing else. For that reason this script never exits non-zero: a
cache problem must not be able to fail the whole deployment.

Usage:

    python unpack_precomputed.py
"""

import gzip
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

TARGETS = [
    "precomputed/rdkit_cache.db",
    "precomputed/homologs.db",
]


def unpack(relative_path):

    target = BASE_DIR / relative_path

    source = Path(str(target) + ".gz")

    if target.exists():
        print(f"  {target.name}: already unpacked")
        return

    if not source.exists():
        print(f"  {target.name}: {source.name} not found - skipping "
              "(the app will run without this cache)")
        return

    temporary = Path(str(target) + ".tmp")

    try:

        target.parent.mkdir(parents=True, exist_ok=True)

        with gzip.open(source, "rb") as src, open(temporary, "wb") as dst:
            shutil.copyfileobj(src, dst, 4 * 1024 * 1024)

        temporary.replace(target)

        source.unlink()

        size = target.stat().st_size / 1e6

        print(f"  {target.name}: unpacked ({size:.1f} MB)")

    except Exception as error:

        print(f"  {target.name}: could not unpack ({error}); "
              "the app will unpack it on first use instead")

        if temporary.exists():

            try:
                temporary.unlink()
            except OSError:
                pass


if __name__ == "__main__":

    print("Unpacking precomputed caches:")

    for item in TARGETS:
        unpack(item)

    # Never fail the build over a cache
    sys.exit(0)
