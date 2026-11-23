"""
Stereochemistry lookup (see build_stereo_cache.py).

Stereoisomers share their atoms and bonds, so the scaffold grouping and the
one-atom-difference analysis cannot tell them apart. This service reads the
precomputed stereoisomer groups: molecules that are the same flat structure
but differ in three-dimensional arrangement, with how much their potency
differs.

If the cache file is missing the service reports itself unavailable and the
rest of the application carries on exactly as before.
"""

import csv
import gzip
import io
import json
import os
import shutil
import sqlite3
import threading
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import rdDepictor
from rdkit.Chem.Draw import rdMolDraw2D

from app.services.database_service import DatabaseService


class StereoCacheService:

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    DEFAULT_PATH = BASE_DIR / "precomputed" / "stereo.db"

    CLIFF_MODERATE = 1.0
    CLIFF_STRONG = 2.0

    _lock = threading.Lock()
    _available = None
    _path = None
    _parameters = {}

    # --------------------------------------------------
    # LOCATE / OPEN
    # --------------------------------------------------

    @classmethod
    def get_path(cls):

        env_path = os.getenv("STEREO_DB_PATH")

        if env_path:
            return Path(env_path)

        return cls.DEFAULT_PATH

    @classmethod
    def _prepare_file(cls, path):

        if path.exists():
            return True

        gz_path = Path(str(path) + ".gz")

        if not gz_path.exists():
            return False

        tmp = Path(str(path) + ".tmp")

        with gzip.open(gz_path, "rb") as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, length=4 * 1024 * 1024)

        tmp.replace(path)

        return True

    @classmethod
    def is_available(cls):

        if cls._available is not None:
            return cls._available

        with cls._lock:

            if cls._available is not None:
                return cls._available

            path = cls.get_path()

            try:

                if not cls._prepare_file(path):
                    print(f"Stereo cache not found at {path}; "
                          "stereochemistry analysis is disabled.")
                    cls._available = False
                    return False

                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

                row = conn.execute(
                    "SELECT value FROM stereo_meta WHERE key = 'parameters'"
                ).fetchone()

                count = conn.execute(
                    "SELECT COUNT(*) FROM stereo_targets"
                ).fetchone()[0]

                conn.close()

                cls._parameters = json.loads(row[0]) if row else {}
                cls._path = path
                cls._available = True

                print(f"Using stereo cache: {path} ({count} targets)")

            except Exception as error:

                print(f"Stereo cache could not be opened ({error}); "
                      "stereochemistry analysis is disabled.")

                cls._available = False

            return cls._available

    @classmethod
    def _conn(cls):

        conn = getattr(threading.current_thread(), "_stereo_conn", None)

        if conn is None:

            conn = sqlite3.connect(
                f"file:{cls._path}?mode=ro",
                uri=True,
                check_same_thread=False
            )

            conn.row_factory = sqlite3.Row

            threading.current_thread()._stereo_conn = conn

        return conn

    # --------------------------------------------------
    # LOOKUPS
    # --------------------------------------------------

    @classmethod
    def get_target(cls, uniprot_id):

        row = cls._conn().execute(
            "SELECT * FROM stereo_targets WHERE uniprot_id = ? LIMIT 1",
            (uniprot_id,)
        ).fetchone()

        return dict(row) if row else None

    @classmethod
    def parameters(cls):

        return dict(cls._parameters)

    @staticmethod
    def _label(group_no):

        return f"STEREO_{group_no:04d}"

    @classmethod
    def _group_row(cls, row):

        delta = row["delta"]

        if delta is None:
            flag = None
        elif delta >= cls.CLIFF_STRONG:
            flag = "strong"
        elif delta >= cls.CLIFF_MODERATE:
            flag = "moderate"
        else:
            flag = None

        return {
            "group_id": cls._label(row["group_no"]),
            "group_no": row["group_no"],
            "isomers": row["isomers"],
            "with_activity": row["with_activity"],
            "relationship": row["relationship"],
            "pic50_best": row["pic50_best"],
            "pic50_worst": row["pic50_worst"],
            "delta_pic50": delta,
            "fold_change": (10 ** delta) if delta is not None else None,
            "cliff": flag,
            "enantiomer_pairs": row["enantiomer_pairs"],
            "flat_smiles": row["flat_smiles"],
        }

    @classmethod
    def get_groups(
        cls,
        target_chembl_id,
        offset=0,
        limit=25,
        min_delta=0.0,
        relationship=None
    ):
        """One page of stereoisomer groups, largest potency gap first."""

        where = "target_chembl_id = ? AND delta IS NOT NULL AND delta >= ?"
        params = [target_chembl_id, float(min_delta)]

        if relationship:
            where += " AND relationship = ?"
            params.append(relationship)

        total = cls._conn().execute(
            f"SELECT COUNT(*) FROM stereo_groups WHERE {where}", params
        ).fetchone()[0]

        rows = cls._conn().execute(
            f"SELECT * FROM stereo_groups WHERE {where} "
            "ORDER BY delta DESC, group_no LIMIT ? OFFSET ?",
            params + [int(limit), int(offset)]
        ).fetchall()

        return total, [cls._group_row(r) for r in rows]

    @classmethod
    def relationship_counts(cls, target_chembl_id):

        rows = cls._conn().execute(
            "SELECT relationship, COUNT(*) FROM stereo_groups "
            "WHERE target_chembl_id = ? AND delta IS NOT NULL "
            "GROUP BY relationship",
            (target_chembl_id,)
        ).fetchall()

        return {r[0]: r[1] for r in rows if r[0]}

    # --------------------------------------------------
    # ONE GROUP, WITH EVERY ISOMER DRAWN
    # --------------------------------------------------

    @classmethod
    def get_group_detail(cls, target_chembl_id, group_no, cap=12):

        row = cls._conn().execute(
            "SELECT * FROM stereo_groups "
            "WHERE target_chembl_id = ? AND group_no = ?",
            (target_chembl_id, int(group_no))
        ).fetchone()

        if row is None:
            return None

        data = cls._group_row(row)

        ids = row["members"].split(",") if row["members"] else []

        data["isomer_list"] = cls._load_isomers(
            target_chembl_id, ids, cap
        )

        return data

    @staticmethod
    def _largest_fragment(mol):

        fragments = Chem.GetMolFrags(mol, asMols=True)

        return max(fragments, key=lambda f: f.GetNumHeavyAtoms())

    @classmethod
    def _describe(cls, mol):
        """Short CIP-style description, e.g. 'R,S' or '1 unspecified'."""

        centres = Chem.FindMolChiralCenters(
            mol, includeUnassigned=True, useLegacyImplementation=False
        )

        labels = sorted(c[1] for c in centres)

        for bond in mol.GetBonds():

            stereo = bond.GetStereo()

            if stereo in (Chem.BondStereo.STEREOE, Chem.BondStereo.STEREOZ):

                labels.append(
                    "E" if stereo == Chem.BondStereo.STEREOE else "Z"
                )

        return ",".join(labels).replace("?", "unspecified")

    @classmethod
    def _draw(cls, mol, width=260, height=200):

        try:

            rdDepictor.Compute2DCoords(mol)

            drawer = rdMolDraw2D.MolDraw2DSVG(width, height)

            drawer.drawOptions().addStereoAnnotation = True

            drawer.DrawMolecule(mol)

            drawer.FinishDrawing()

            return drawer.GetDrawingText()

        except Exception:

            return None

    @classmethod
    def _load_isomers(cls, target_chembl_id, ids, cap):

        ids = ids[:cap * 3]

        if not ids:
            return []

        conn = sqlite3.connect(
            f"file:{DatabaseService.get_database_path()}?mode=ro",
            uri=True
        )

        try:

            marks = ",".join("?" * len(ids))

            rows = conn.execute(
                f"""
                SELECT molecule_chembl_id, canonical_smiles,
                       AVG(CAST(pchembl_value AS REAL))
                FROM activities
                WHERE target_chembl_id = ?
                  AND molecule_chembl_id IN ({marks})
                  AND standard_relation = '='
                  AND canonical_smiles IS NOT NULL
                GROUP BY molecule_chembl_id
                """,
                [target_chembl_id] + ids
            ).fetchall()

        finally:
            conn.close()

        isomers = []

        seen = set()

        for chembl_id, smiles, pic50 in rows:

            mol = Chem.MolFromSmiles(smiles)

            if mol is None:
                continue

            mol = cls._largest_fragment(mol)

            key = Chem.MolToSmiles(mol)

            if key in seen:
                continue

            seen.add(key)

            isomers.append({
                "chembl_id": chembl_id,
                "smiles": key,
                "pic50": pic50,
                "stereo": cls._describe(mol),
                "svg": cls._draw(mol),
            })

        isomers.sort(
            key=lambda i: i["pic50"] if i["pic50"] is not None else -1,
            reverse=True
        )

        best = isomers[0]["pic50"] if isomers and isomers[0]["pic50"] is not None else None

        for isomer in isomers:

            isomer["delta_from_best"] = (
                best - isomer["pic50"]
                if best is not None and isomer["pic50"] is not None
                else None
            )

        return isomers[:cap]

    # --------------------------------------------------
    # CSV EXPORT
    # --------------------------------------------------

    COLUMNS = [
        "target_chembl_id", "target_name", "uniprot_id", "group_id",
        "isomers", "relationship", "pic50_best", "pic50_worst",
        "delta_pic50", "fold_change", "cliff", "enantiomer_pairs",
        "flat_smiles",
    ]

    @classmethod
    def to_csv(cls, target):

        handle = io.StringIO()

        writer = csv.writer(handle)

        writer.writerow(cls.COLUMNS)

        rows = cls._conn().execute(
            "SELECT * FROM stereo_groups WHERE target_chembl_id = ? "
            "AND delta IS NOT NULL ORDER BY delta DESC, group_no",
            (target["target_chembl_id"],)
        ).fetchall()

        for row in rows:

            g = cls._group_row(row)

            writer.writerow([
                target["target_chembl_id"],
                target["target_name"],
                target["uniprot_id"],
                g["group_id"],
                g["isomers"],
                g["relationship"] or "",
                f"{g['pic50_best']:.2f}",
                f"{g['pic50_worst']:.2f}",
                f"{g['delta_pic50']:.2f}",
                f"{g['fold_change']:.1f}",
                g["cliff"] or "",
                g["enantiomer_pairs"],
                g["flat_smiles"],
            ])

        return handle.getvalue()
