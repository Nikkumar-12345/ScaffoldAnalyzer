"""
Build the precomputed RDKit cache used by the analysis pipeline.

Every value stored here is produced by the SAME functions the live
pipeline uses (MurckoScaffold, SideChainService.get_side_chain,
DescriptorService.calculate, FunctionalGroupService.detect), so the
analysis results are identical whether a value comes from this cache
or is computed on the fly. Anything missing from the cache (for
example molecules downloaded through the ChEMBL API fallback) is still
computed live, so the cache is purely an accelerator.

Usage (from the backend folder):

    python build_precomputed_cache.py <path-to-chembl.db> [output.db]

Rebuild it whenever the ChEMBL database or the RDKit version changes.
"""

import os
import sqlite3
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from rdkit import Chem, RDLogger
from rdkit.Chem.Scaffolds import MurckoScaffold

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.services.precomputed_service import (  # noqa: E402
    PrecomputedService,
    smiles_hash,
)
from app.services.side_chain_service import SideChainService  # noqa: E402
from app.services.descriptor_service import DescriptorService  # noqa: E402
from app.services.functional_group_service import (  # noqa: E402
    FunctionalGroupService,
)

RDLogger.DisableLog("rdApp.*")

DEFAULT_OUTPUT = BASE_DIR / "precomputed" / "rdkit_cache.db"


# ------------------------------------------------------------
# PER-MOLECULE WORK  (mirrors ScaffoldService exactly)
# ------------------------------------------------------------

def process_molecule(smiles):

    h = smiles_hash(smiles)

    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return (h, PrecomputedService.STATUS_INVALID, None, None, 0)

    try:
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
    except Exception:
        return (h, PrecomputedService.STATUS_INVALID, None, None, 0)

    if scaffold is None or scaffold.GetNumAtoms() == 0:
        return (h, PrecomputedService.STATUS_NO_SCAFFOLD, None, None, 0)

    scaffold_smiles = Chem.MolToSmiles(scaffold, canonical=True)

    if not scaffold_smiles:
        return (h, PrecomputedService.STATUS_NO_SCAFFOLD, None, None, 0)

    side_chain = SideChainService.get_side_chain(smiles, scaffold_smiles)

    return (
        h,
        PrecomputedService.STATUS_OK,
        scaffold_smiles,
        side_chain,
        1 if side_chain is not None else 0,
    )


def process_molecule_batch(batch):
    return [process_molecule(s) for s in batch]


# ------------------------------------------------------------
# PER-SCAFFOLD WORK
# ------------------------------------------------------------

def process_scaffold(scaffold_smiles):

    descriptors = DescriptorService.calculate(scaffold_smiles)
    groups = FunctionalGroupService.detect(scaffold_smiles)

    return PrecomputedService.encode_scaffold_row(
        scaffold_smiles,
        descriptors,
        groups,
    )


def process_scaffold_batch(batch):
    return [process_scaffold(s) for s in batch]


def batches(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def build(chembl_db, output):

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    tmp = output.with_suffix(".building")

    if tmp.exists():
        tmp.unlink()

    print(f"Reading SMILES from {chembl_db} ...")

    src = sqlite3.connect(str(chembl_db))

    smiles_list = [
        row[0]
        for row in src.execute(
            "SELECT DISTINCT canonical_smiles FROM activities "
            "WHERE canonical_smiles IS NOT NULL AND canonical_smiles != ''"
        )
    ]

    src.close()

    print(f"Distinct molecule SMILES: {len(smiles_list):,}")

    out = sqlite3.connect(str(tmp))
    PrecomputedService.create_schema(out)

    workers = max(1, os.cpu_count() or 1)
    print(f"Using {workers} worker process(es)")

    scaffold_set = set()
    start = time.time()
    done = 0

    with Pool(workers) as pool:

        for result in pool.imap_unordered(
            process_molecule_batch,
            batches(smiles_list, 2000),
        ):

            rows = []

            for h, status, scaffold_smiles, side_chain, has_sc in result:

                scaffold_h = None

                if scaffold_smiles is not None:
                    scaffold_set.add(scaffold_smiles)
                    scaffold_h = smiles_hash(scaffold_smiles)

                rows.append((h, status, scaffold_h, side_chain, has_sc))

            out.executemany(
                "INSERT OR REPLACE INTO molecules "
                "(h, status, scaffold_h, side_chain, has_side_chain) "
                "VALUES (?, ?, ?, ?, ?)",
                rows,
            )

            done += len(result)

            if done % 50000 < 2000:
                rate = done / max(time.time() - start, 1e-6)
                print(f"  molecules {done:,}/{len(smiles_list):,} "
                      f"({rate:,.0f}/s)")

        out.commit()

        scaffolds = sorted(scaffold_set)
        print(f"Distinct scaffolds: {len(scaffolds):,}")

        start = time.time()
        done = 0

        for result in pool.imap_unordered(
            process_scaffold_batch,
            batches(scaffolds, 1000),
        ):

            out.executemany(
                PrecomputedService.SCAFFOLD_INSERT_SQL,
                result,
            )

            done += len(result)

            if done % 20000 < 1000:
                rate = done / max(time.time() - start, 1e-6)
                print(f"  scaffolds {done:,}/{len(scaffolds):,} "
                      f"({rate:,.0f}/s)")

    out.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("rdkit_version", Chem.rdBase.rdkitVersion),
    )
    out.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        ("schema_version", str(PrecomputedService.SCHEMA_VERSION)),
    )
    out.commit()
    out.execute("VACUUM")
    out.close()

    tmp.replace(output)

    print(f"Done: {output} ({output.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    build(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT,
    )
