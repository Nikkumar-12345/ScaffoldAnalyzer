"""
Chemical series / maximum-common-substructure lookup
(see build_mcs_cache.py and mcs_service.py).

Every target with activity data was clustered into chemical series and
the maximum common substructure of each series was extracted offline.
The results are stored here, so showing them at runtime is a plain
database lookup - no clustering and no MCS search while a user waits.

If the cache file is missing the service reports itself unavailable and
the rest of the application carries on exactly as before.
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

from app.services.database_service import DatabaseService
from app.services.mcs_service import MCSService


class MCSCacheService:

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    DEFAULT_PATH = BASE_DIR / "precomputed" / "mcs_series.db"

    _lock = threading.Lock()
    _available = None
    _path = None
    _parameters = {}

    # --------------------------------------------------
    # LOCATE / OPEN
    # --------------------------------------------------

    @classmethod
    def get_path(cls):

        env_path = os.getenv("MCS_DB_PATH")

        if env_path:
            return Path(env_path)

        return cls.DEFAULT_PATH

    @classmethod
    def _prepare_file(cls, path):
        """Decompress <path>.gz next to it on first use if needed."""

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
                    print(f"MCS cache not found at {path}; "
                          "chemical-series analysis is disabled.")
                    cls._available = False
                    return False

                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

                row = conn.execute(
                    "SELECT value FROM mcs_meta WHERE key = 'parameters'"
                ).fetchone()

                count = conn.execute(
                    "SELECT COUNT(*) FROM mcs_targets"
                ).fetchone()[0]

                conn.close()

                cls._parameters = json.loads(row[0]) if row else {}
                cls._path = path
                cls._available = True

                print(f"Using MCS cache: {path} ({count} targets)")

            except Exception as error:

                print(f"MCS cache could not be opened ({error}); "
                      "chemical-series analysis is disabled.")

                cls._available = False

            return cls._available

    @classmethod
    def _conn(cls):

        conn = getattr(threading.current_thread(), "_mcs_conn", None)

        if conn is None:

            conn = sqlite3.connect(
                f"file:{cls._path}?mode=ro",
                uri=True,
                check_same_thread=False
            )

            conn.row_factory = sqlite3.Row

            threading.current_thread()._mcs_conn = conn

        return conn

    # --------------------------------------------------
    # LOOKUPS
    # --------------------------------------------------

    @classmethod
    def get_target(cls, uniprot_id):

        row = cls._conn().execute(
            "SELECT * FROM mcs_targets WHERE uniprot_id = ? LIMIT 1",
            (uniprot_id,)
        ).fetchone()

        return dict(row) if row else None

    @classmethod
    def parameters(cls):

        return dict(cls._parameters)

    @staticmethod
    def _series_label(series_no):

        return f"SERIES_{series_no:04d}"

    @classmethod
    def _series_row(cls, row, with_members=False):

        data = {
            "chemical_series_id": cls._series_label(row["series_no"]),
            "series_no": row["series_no"],
            "number_of_molecules": row["molecules"],
            "scaffolds_in_series": row["scaffolds"],
            "mcs_status": row["status"],
            "mcs_smarts": row["smarts"],
            "mcs_atoms": row["atoms"],
            "mcs_bonds": row["bonds"],
            "mcs_coverage": row["coverage"],
            "activity": {
                "count": row["pic50_count"],
                "median_pic50": row["pic50_median"],
                "min_pic50": row["pic50_min"],
                "max_pic50": row["pic50_max"],
            },
            "representative": {
                "chembl_id": row["rep_chembl_id"],
                "smiles": row["rep_smiles"],
            },
        }

        if with_members:
            data["member_ids"] = (
                row["members"].split(",") if row["members"] else []
            )

        return data

    @classmethod
    def get_series(
        cls,
        target_chembl_id,
        offset=0,
        limit=25,
        min_size=1,
        with_mcs_only=False
    ):
        """One page of a target's chemical series, largest first."""

        where = "target_chembl_id = ? AND molecules >= ?"
        params = [target_chembl_id, int(min_size)]

        if with_mcs_only:
            where += " AND smarts IS NOT NULL"

        total = cls._conn().execute(
            f"SELECT COUNT(*) FROM mcs_series WHERE {where}", params
        ).fetchone()[0]

        rows = cls._conn().execute(
            f"SELECT * FROM mcs_series WHERE {where} "
            "ORDER BY series_no LIMIT ? OFFSET ?",
            params + [int(limit), int(offset)]
        ).fetchall()

        return total, [cls._series_row(r) for r in rows]

    @classmethod
    def get_series_detail(cls, target_chembl_id, series_no, draw=True):
        """One series with its molecules and structure images."""

        row = cls._conn().execute(
            "SELECT * FROM mcs_series "
            "WHERE target_chembl_id = ? AND series_no = ?",
            (target_chembl_id, int(series_no))
        ).fetchone()

        if row is None:
            return None

        data = cls._series_row(row, with_members=True)

        ids = data.pop("member_ids")

        data["molecules"] = cls._load_molecules(target_chembl_id, ids)

        data["mcs_svg"] = None
        data["representative_svg"] = None

        if draw and data["mcs_smarts"]:

            data["mcs_svg"] = MCSService.draw_mcs(data["mcs_smarts"])

            rep = Chem.MolFromSmiles(data["representative"]["smiles"] or "")

            if rep is not None:
                data["representative_svg"] = MCSService.draw_with_highlight(
                    rep, data["mcs_smarts"]
                )

        return data

    @classmethod
    def _load_molecules(cls, target_chembl_id, ids, cap=500):
        """Molecule ids -> smiles and pIC50 from the main database."""

        ids = ids[:cap]

        if not ids:
            return []

        conn = sqlite3.connect(
            f"file:{DatabaseService.get_database_path()}?mode=ro",
            uri=True
        )

        try:

            found = {}

            for start in range(0, len(ids), 500):

                chunk = ids[start:start + 500]

                marks = ",".join("?" * len(chunk))

                for chembl_id, smiles, pchembl in conn.execute(
                    f"""
                    SELECT molecule_chembl_id, canonical_smiles,
                           pchembl_value
                    FROM activities
                    WHERE target_chembl_id = ?
                      AND molecule_chembl_id IN ({marks})
                      AND standard_relation = '='
                      AND canonical_smiles IS NOT NULL
                    GROUP BY molecule_chembl_id
                    """,
                    [target_chembl_id] + chunk
                ):

                    try:
                        pic50 = float(pchembl) if pchembl not in (
                            None, ""
                        ) else None
                    except (TypeError, ValueError):
                        pic50 = None

                    found[chembl_id] = {
                        "chembl_id": chembl_id,
                        "smiles": smiles,
                        "pic50": pic50,
                    }

        finally:
            conn.close()

        molecules = [found[i] for i in ids if i in found]

        molecules.sort(
            key=lambda m: m["pic50"] if m["pic50"] is not None else -1,
            reverse=True
        )

        return molecules

    # --------------------------------------------------
    # CSV EXPORT (same columns as MCSService.CSV_COLUMNS)
    # --------------------------------------------------

    @classmethod
    def to_csv(cls, target):

        handle = io.StringIO()

        writer = csv.writer(handle)

        writer.writerow(MCSService.CSV_COLUMNS)

        rows = cls._conn().execute(
            "SELECT * FROM mcs_series WHERE target_chembl_id = ? "
            "ORDER BY series_no",
            (target["target_chembl_id"],)
        ).fetchall()

        for row in rows:

            writer.writerow([
                target["target_chembl_id"],
                target["target_name"],
                target["uniprot_id"],
                cls._series_label(row["series_no"]),
                row["molecules"],
                row["scaffolds"],
                row["status"],
                row["smarts"] or "",
                row["atoms"] if row["atoms"] is not None else "",
                row["bonds"] if row["bonds"] is not None else "",
            ])

        return handle.getvalue()
