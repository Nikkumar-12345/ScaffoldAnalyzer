"""
Build the precomputed stereochemistry cache.

For every target in the local ChEMBL database that has activity data, this
script finds the molecules that are the SAME flat structure but differ in
their three-dimensional arrangement (stereoisomers), and records how much
their potency differs.

Why this is a separate analysis
-------------------------------
Everything else in the application treats a molecule as a flat graph. Two
stereoisomers have identical atoms and bonds, so the scaffold grouping puts
them together and the one-atom-difference analysis sees no difference at
all. Yet stereoisomers can differ in potency by orders of magnitude (one
enantiomer of a drug is often the active one), and that is exactly the
information a chemist wants.

Method
------
1.  Keep the largest fragment of each molecule (drops salts and solvents).
2.  Two keys per molecule:
        flat key       canonical SMILES with stereochemistry removed
        isomeric key   canonical SMILES with stereochemistry
3.  Molecules sharing a flat key but having different isomeric keys form a
    stereoisomer group.
4.  For each group:
        - relationship of the most-different pair of isomers:
              Enantiomers   every centre inverted (mirror images)
              Diastereomers some centres differ
              E/Z isomers   only a double bond differs
              Specified vs unspecified   one has undefined stereochemistry
        - highest and lowest pIC50, the difference and the fold change
        - number of enantiomer pairs and the largest enantiomer fold
          change (the "eudismic ratio" when it is an enantiomer pair)
5.  Per target: how many molecules have stereocentres, how many are fully
    specified, and how many stereo groups, pairs and cliffs there are.

The result is one SQLite file. Run once; the application only reads it.

Usage (from the backend folder):

    python build_stereo_cache.py <path-to-chembl.db> [output.db] [--workers N]
"""

import gzip
import json
import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

DEFAULT_OUTPUT = BASE_DIR / "precomputed" / "stereo.db"

CLIFF_MODERATE = 1.0
CLIFF_STRONG = 2.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS stereo_targets (
    target_chembl_id    TEXT PRIMARY KEY,
    uniprot_id          TEXT,
    target_name         TEXT,
    molecules           INTEGER,
    with_stereocentres  INTEGER,
    fully_specified     INTEGER,
    partly_specified    INTEGER,
    groups_total        INTEGER,
    groups_with_activity INTEGER,
    enantiomer_pairs    INTEGER,
    diastereomer_groups INTEGER,
    ez_groups           INTEGER,
    cliffs_moderate     INTEGER,
    cliffs_strong       INTEGER,
    max_delta           REAL
);

CREATE TABLE IF NOT EXISTS stereo_groups (
    target_chembl_id TEXT NOT NULL,
    group_no         INTEGER NOT NULL,
    isomers          INTEGER,
    with_activity    INTEGER,
    relationship     TEXT,
    pic50_best       REAL,
    pic50_worst      REAL,
    delta            REAL,
    enantiomer_pairs INTEGER,
    enantiomer_delta REAL,
    flat_smiles      TEXT,
    members          TEXT,
    PRIMARY KEY (target_chembl_id, group_no)
);

CREATE TABLE IF NOT EXISTS stereo_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

REL_ENANTIOMERS = "Enantiomers"
REL_DIASTEREOMERS = "Diastereomers"
REL_EZ = "E/Z isomers"
REL_UNSPECIFIED = "Specified vs unspecified"


def mirror_key(isomeric_smiles):
    """Isomeric SMILES of the mirror image (every tetrahedral centre flipped)."""

    from rdkit import Chem

    swapped = (
        isomeric_smiles.replace("@@", "\x00")
        .replace("@", "@@")
        .replace("\x00", "@")
    )

    mol = Chem.MolFromSmiles(swapped)

    return Chem.MolToSmiles(mol) if mol is not None else None


def analyse_molecule(smiles):
    """
    (flat_key, isomeric_key, tetra, tetra_specified, bonds, bonds_specified)
    for the largest fragment of the molecule, or None if it cannot be parsed.
    """

    from rdkit import Chem

    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return None

    if "." in smiles:

        fragments = Chem.GetMolFrags(mol, asMols=True)

        mol = max(fragments, key=lambda f: f.GetNumHeavyAtoms())

    flat = Chem.MolToSmiles(mol, isomericSmiles=False)

    isomeric = Chem.MolToSmiles(mol)

    tetra = tetra_spec = bonds = bonds_spec = 0

    for info in Chem.FindPotentialStereo(mol):

        specified = info.specified == Chem.StereoSpecified.Specified

        if info.type == Chem.StereoType.Atom_Tetrahedral:
            tetra += 1
            tetra_spec += 1 if specified else 0

        elif info.type == Chem.StereoType.Bond_Double:
            bonds += 1
            bonds_spec += 1 if specified else 0

    return flat, isomeric, tetra, tetra_spec, bonds, bonds_spec


def load_target(conn, target_chembl_id):
    """One row per molecule: id, smiles, mean pChEMBL value."""

    return conn.execute(
        """
        SELECT molecule_chembl_id, canonical_smiles,
               AVG(CAST(pchembl_value AS REAL))
        FROM activities
        WHERE target_chembl_id = ?
          AND standard_relation = '='
          AND canonical_smiles IS NOT NULL
          AND standard_value IS NOT NULL
        GROUP BY molecule_chembl_id
        """,
        (target_chembl_id,)
    ).fetchall()


def analyse_target(rows):
    """Returns (target_summary, groups) for one target's molecules."""

    records = []

    for molecule_id, smiles, pic50 in rows:

        parsed = analyse_molecule(smiles)

        if parsed is None:
            continue

        records.append((molecule_id, pic50, parsed))

    with_centres = fully = partly = 0

    by_flat = defaultdict(list)

    for molecule_id, pic50, (flat, iso, t, ts, b, bs) in records:

        total = t + b

        if total:
            with_centres += 1

            if ts + bs == total:
                fully += 1
            elif ts + bs > 0:
                partly += 1

        by_flat[flat].append((molecule_id, pic50, iso, t, ts, b, bs))

    groups = []

    for flat, members in by_flat.items():

        isomeric_keys = {m[2] for m in members}

        if len(isomeric_keys) < 2:
            continue

        graded = [m for m in members if m[1] is not None]

        # one representative molecule per isomeric key (best potency)
        per_key = {}

        for m in graded:
            current = per_key.get(m[2])
            if current is None or m[1] > current[1]:
                per_key[m[2]] = m

        relationship = None
        best = worst = delta = None
        pairs = 0
        pair_delta = None

        def is_specified(m):
            return (m[4] + m[6]) == (m[3] + m[5])

        if len(per_key) >= 2:

            ranked = sorted(per_key.values(), key=lambda m: m[1], reverse=True)

            top, bottom = ranked[0], ranked[-1]

            best, worst = top[1], bottom[1]
            delta = best - worst

            if not (is_specified(top) and is_specified(bottom)):
                relationship = REL_UNSPECIFIED

            else:

                mirror = mirror_key(top[2])

                if mirror == bottom[2]:
                    relationship = REL_ENANTIOMERS

                elif top[3] == bottom[3] and top[5] == bottom[5]:
                    # same number of centres: only a bond may differ
                    top_centres = Chem_centres(top[2])
                    bottom_centres = Chem_centres(bottom[2])

                    relationship = (
                        REL_EZ if top_centres == bottom_centres
                        else REL_DIASTEREOMERS
                    )

                else:
                    relationship = REL_DIASTEREOMERS

            # enantiomer pairs inside the group
            keys = set(per_key)

            for key, m in per_key.items():

                if not is_specified(m):
                    continue

                other = per_key.get(mirror_key(key))

                if other is not None and other[2] != key:
                    pairs += 1
                    spread = abs(m[1] - other[1])
                    pair_delta = spread if pair_delta is None else max(pair_delta, spread)

            pairs //= 2

        else:
            relationship = REL_UNSPECIFIED if any(
                not is_specified(m) for m in members
            ) else None

        groups.append({
            "flat": flat,
            "isomers": len(isomeric_keys),
            "with_activity": len(per_key),
            "relationship": relationship,
            "best": best,
            "worst": worst,
            "delta": delta,
            "enantiomer_pairs": pairs,
            "enantiomer_delta": pair_delta,
            "members": ",".join(
                f"{m[0]}" for m in sorted(
                    members,
                    key=lambda m: m[1] if m[1] is not None else -1,
                    reverse=True
                )
            ),
        })

    groups.sort(key=lambda g: (g["delta"] is None, -(g["delta"] or 0)))

    summary = {
        "molecules": len(records),
        "with_stereocentres": with_centres,
        "fully_specified": fully,
        "partly_specified": partly,
        "groups_total": len(groups),
        "groups_with_activity": sum(1 for g in groups if g["delta"] is not None),
        "enantiomer_pairs": sum(g["enantiomer_pairs"] for g in groups),
        "diastereomer_groups": sum(
            1 for g in groups if g["relationship"] == REL_DIASTEREOMERS
        ),
        "ez_groups": sum(1 for g in groups if g["relationship"] == REL_EZ),
        "cliffs_moderate": sum(
            1 for g in groups if g["delta"] is not None and g["delta"] >= CLIFF_MODERATE
        ),
        "cliffs_strong": sum(
            1 for g in groups if g["delta"] is not None and g["delta"] >= CLIFF_STRONG
        ),
        "max_delta": max(
            (g["delta"] for g in groups if g["delta"] is not None), default=None
        ),
    }

    return summary, groups


def Chem_centres(isomeric_smiles):
    """Tetrahedral centre labels, to tell E/Z-only differences apart."""

    from rdkit import Chem

    mol = Chem.MolFromSmiles(isomeric_smiles)

    return tuple(sorted(
        Chem.FindMolChiralCenters(
            mol, includeUnassigned=True, useLegacyImplementation=False
        )
    ))


_worker_conn = None


def init_worker(database_path):

    global _worker_conn

    from rdkit import RDLogger

    RDLogger.DisableLog("rdApp.*")

    _worker_conn = sqlite3.connect(f"file:{database_path}?mode=ro", uri=True)


def process_target(job):

    target_chembl_id, uniprot_id, target_name = job

    started = time.time()

    try:

        rows = load_target(_worker_conn, target_chembl_id)

        summary, groups = analyse_target(rows)

        error = None

    except Exception as exc:

        summary, groups = None, []

        error = f"{type(exc).__name__}: {exc}"

    return {
        "job": job,
        "summary": summary,
        "groups": groups,
        "error": error,
        "seconds": time.time() - started,
    }


def store(out, payload):

    target_chembl_id, uniprot_id, target_name = payload["job"]

    s = payload["summary"]

    out.execute(
        "INSERT OR REPLACE INTO stereo_targets VALUES "
        "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            target_chembl_id, uniprot_id, target_name,
            s["molecules"], s["with_stereocentres"], s["fully_specified"],
            s["partly_specified"], s["groups_total"],
            s["groups_with_activity"], s["enantiomer_pairs"],
            s["diastereomer_groups"], s["ez_groups"], s["cliffs_moderate"],
            s["cliffs_strong"], s["max_delta"],
        )
    )

    out.execute(
        "DELETE FROM stereo_groups WHERE target_chembl_id = ?",
        (target_chembl_id,)
    )

    for number, g in enumerate(payload["groups"], start=1):

        out.execute(
            "INSERT INTO stereo_groups VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                target_chembl_id, number, g["isomers"], g["with_activity"],
                g["relationship"], g["best"], g["worst"], g["delta"],
                g["enantiomer_pairs"], g["enantiomer_delta"], g["flat"],
                g["members"],
            )
        )

    out.commit()


def main():

    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    workers = 2

    if "--workers" in sys.argv:
        workers = int(sys.argv[sys.argv.index("--workers") + 1])
        args = [a for a in args if a != str(workers)]

    if not args:
        print(__doc__)
        sys.exit(1)

    database_path = Path(args[0])

    output = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT

    output.parent.mkdir(parents=True, exist_ok=True)

    out = sqlite3.connect(output)

    out.executescript(SCHEMA)

    source = sqlite3.connect(database_path)

    targets = source.execute(
        """
        SELECT t.target_chembl_id, t.uniprot_id, t.target_name, c.n
        FROM targets t
        JOIN (
            SELECT target_chembl_id, COUNT(DISTINCT molecule_chembl_id) n
            FROM activities
            WHERE standard_relation = '='
              AND canonical_smiles IS NOT NULL
              AND standard_value IS NOT NULL
            GROUP BY target_chembl_id
        ) c ON c.target_chembl_id = t.target_chembl_id
        WHERE t.uniprot_id IS NOT NULL
        ORDER BY c.n DESC
        """
    ).fetchall()

    source.close()

    done = {
        row[0] for row in out.execute(
            "SELECT target_chembl_id FROM stereo_targets"
        )
    }

    jobs = [(t[0], t[1], t[2]) for t in targets if t[0] not in done]

    print(
        f"{len(targets)} targets, {len(done)} done, {len(jobs)} to build "
        f"({workers} workers)",
        flush=True
    )

    out.execute(
        "INSERT OR REPLACE INTO stereo_meta VALUES (?, ?)",
        (
            "parameters",
            json.dumps({
                "key_flat": "canonical SMILES without stereochemistry",
                "key_isomeric": "canonical SMILES with stereochemistry",
                "fragment": "largest fragment kept",
                "potency": "mean pChEMBL value per molecule",
                "cliff_moderate": CLIFF_MODERATE,
                "cliff_strong": CLIFF_STRONG,
            })
        )
    )

    out.commit()

    started = time.time()

    finished = 0

    with Pool(
        workers, initializer=init_worker, initargs=(str(database_path),)
    ) as pool:

        for payload in pool.imap_unordered(process_target, jobs, chunksize=1):

            if payload["error"]:
                print(f"  ! {payload['job'][0]}: {payload['error']}", flush=True)
                continue

            store(out, payload)

            finished += 1

            if finished % 200 == 0:
                print(
                    f"{finished}/{len(jobs)} targets, "
                    f"{(time.time() - started) / 60:.1f} min",
                    flush=True
                )

    out.execute("VACUUM")
    out.close()

    gz_path = Path(str(output) + ".gz")

    with open(output, "rb") as src, gzip.open(
        gz_path, "wb", compresslevel=9
    ) as dst:
        shutil.copyfileobj(src, dst)

    print(
        f"Done in {(time.time() - started) / 60:.1f} min. "
        f"{output} ({output.stat().st_size / 1e6:.1f} MB), "
        f"{gz_path} ({gz_path.stat().st_size / 1e6:.1f} MB)",
        flush=True
    )


if __name__ == "__main__":
    main()
