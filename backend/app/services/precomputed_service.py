"""
Read access to the precomputed RDKit cache (see build_precomputed_cache.py).

The cache stores, for every molecule SMILES in the local ChEMBL database:
    - whether it parses / has a Murcko scaffold
    - its Murcko scaffold SMILES
    - its side chain relative to that scaffold
and, for every scaffold:
    - its descriptors and functional groups

All values were produced by the exact same functions the live pipeline
uses, with the same RDKit version (checked at start-up). If the cache
file is missing, or was built with a different RDKit version, the
service reports itself as unavailable and the pipeline silently falls
back to computing everything live - results are identical either way.
"""

import gzip
import hashlib
import os
import shutil
import sqlite3
import threading
from pathlib import Path

from rdkit import Chem

from app.services.functional_group_service import FunctionalGroupService


def smiles_hash(smiles):
    """Stable signed 64-bit hash of a SMILES string (SQLite INTEGER key)."""

    digest = hashlib.blake2b(
        smiles.encode("utf-8"),
        digest_size=8
    ).digest()

    return int.from_bytes(digest, "big", signed=True)


class PrecomputedService:

    SCHEMA_VERSION = 1

    STATUS_OK = 1
    STATUS_NO_SCAFFOLD = 0
    STATUS_INVALID = -1

    # Same order as DescriptorService.calculate() output
    DESCRIPTOR_KEYS = [
        "molecular_weight",
        "logp",
        "tpsa",
        "hba",
        "hbd",
        "rotatable_bonds",
        "fsp3",
        "ring_count",
        "aromatic_rings",
        "heavy_atoms",
        "bertz_complexity",
        "qed",
    ]

    FG_NAMES = list(FunctionalGroupService.PATTERNS.keys())

    SCAFFOLD_INSERT_SQL = (
        "INSERT OR REPLACE INTO scaffolds "
        "(h, smiles, has_descriptors, "
        "molecular_weight, logp, tpsa, hba, hbd, rotatable_bonds, fsp3, "
        "ring_count, aromatic_rings, heavy_atoms, bertz_complexity, qed, "
        "fg_mask) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    DEFAULT_PATH = BASE_DIR / "precomputed" / "rdkit_cache.db"

    _lock = threading.Lock()
    _local = threading.local()
    _available = None
    _path = None

    # --------------------------------------------------
    # SCHEMA (used by the builder)
    # --------------------------------------------------

    @staticmethod
    def create_schema(conn):

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS molecules (
                h INTEGER PRIMARY KEY,
                status INTEGER NOT NULL,
                scaffold_h INTEGER,
                side_chain TEXT,
                has_side_chain INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scaffolds (
                h INTEGER PRIMARY KEY,
                smiles TEXT NOT NULL,
                has_descriptors INTEGER NOT NULL,
                molecular_weight REAL,
                logp REAL,
                tpsa REAL,
                hba INTEGER,
                hbd INTEGER,
                rotatable_bonds INTEGER,
                fsp3 REAL,
                ring_count INTEGER,
                aromatic_rings INTEGER,
                heavy_atoms INTEGER,
                bertz_complexity REAL,
                qed REAL,
                fg_mask INTEGER NOT NULL
            );
            """
        )

    @classmethod
    def encode_scaffold_row(cls, smiles, descriptors, groups):

        mask = 0

        for i, name in enumerate(cls.FG_NAMES):
            if name in groups:
                mask |= 1 << i

        if descriptors is None:
            values = [None] * len(cls.DESCRIPTOR_KEYS)
            has = 0
        else:
            values = [descriptors[k] for k in cls.DESCRIPTOR_KEYS]
            has = 1

        return (smiles_hash(smiles), smiles, has, *values, mask)

    # --------------------------------------------------
    # LOCATE / OPEN
    # --------------------------------------------------

    @classmethod
    def get_path(cls):

        env_path = os.getenv("PRECOMPUTED_DB_PATH")

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
                    print(f"Precomputed RDKit cache not found at {path}; "
                          "computing everything live.")
                    cls._available = False
                    return False

                conn = sqlite3.connect(
                    f"file:{path}?mode=ro",
                    uri=True
                )

                meta = dict(conn.execute("SELECT key, value FROM meta"))
                conn.close()

                built_with = meta.get("rdkit_version")
                running = Chem.rdBase.rdkitVersion

                if built_with != running:
                    print(f"Precomputed cache was built with RDKit "
                          f"{built_with}, but RDKit {running} is running; "
                          "ignoring it so results stay exact.")
                    cls._available = False
                    return False

                if meta.get("schema_version") != str(cls.SCHEMA_VERSION):
                    print("Precomputed cache schema mismatch; ignoring it.")
                    cls._available = False
                    return False

                cls._path = path
                cls._available = True
                print(f"Using precomputed RDKit cache: {path}")

            except Exception as error:

                print(f"Could not open precomputed cache: {error}")
                cls._available = False

            return cls._available

    @classmethod
    def _conn(cls):

        conn = getattr(cls._local, "conn", None)

        if conn is None:
            conn = sqlite3.connect(
                f"file:{cls._path}?mode=ro",
                uri=True,
                check_same_thread=False
            )
            cls._local.conn = conn

        return conn

    # --------------------------------------------------
    # LOOKUPS
    # --------------------------------------------------

    @classmethod
    def lookup_molecules(cls, smiles_list):
        """
        Returns {smiles: (status, scaffold_smiles, has_side_chain,
        side_chain)} for SMILES found in the cache.
        """

        if not cls.is_available() or not smiles_list:
            return {}

        by_hash = {}

        for s in smiles_list:
            by_hash[smiles_hash(s)] = s

        hashes = list(by_hash)
        found = {}
        conn = cls._conn()

        for i in range(0, len(hashes), 900):

            chunk = hashes[i:i + 900]
            marks = ",".join("?" * len(chunk))

            for h, status, scaffold_smiles, side_chain, has_sc in conn.execute(
                "SELECT m.h, m.status, s.smiles, m.side_chain, "
                "m.has_side_chain FROM molecules m "
                "LEFT JOIN scaffolds s ON s.h = m.scaffold_h "
                f"WHERE m.h IN ({marks})",
                chunk,
            ):

                # A STATUS_OK row must resolve to a scaffold SMILES.
                if status == cls.STATUS_OK and scaffold_smiles is None:
                    continue

                found[by_hash[h]] = (
                    status,
                    scaffold_smiles,
                    bool(has_sc),
                    side_chain,
                )

        return found

    @classmethod
    def lookup_scaffolds(cls, scaffold_smiles_list):
        """
        Returns {scaffold_smiles: (descriptors_or_None, functional_groups)}
        """

        if not cls.is_available() or not scaffold_smiles_list:
            return {}

        by_hash = {smiles_hash(s): s for s in scaffold_smiles_list}
        hashes = list(by_hash)
        found = {}
        conn = cls._conn()
        n_desc = len(cls.DESCRIPTOR_KEYS)

        for i in range(0, len(hashes), 900):

            chunk = hashes[i:i + 900]
            marks = ",".join("?" * len(chunk))

            for row in conn.execute(
                "SELECT h, smiles, has_descriptors, "
                "molecular_weight, logp, tpsa, hba, hbd, rotatable_bonds, "
                "fsp3, ring_count, aromatic_rings, heavy_atoms, "
                "bertz_complexity, qed, fg_mask "
                f"FROM scaffolds WHERE h IN ({marks})",
                chunk,
            ):

                h, smiles, has_desc = row[0], row[1], row[2]

                # Guard against (astronomically unlikely) hash collisions
                if by_hash.get(h) != smiles:
                    continue

                values = row[3:3 + n_desc]
                mask = row[3 + n_desc]

                descriptors = (
                    dict(zip(cls.DESCRIPTOR_KEYS, values))
                    if has_desc else None
                )

                groups = [
                    name
                    for j, name in enumerate(cls.FG_NAMES)
                    if mask & (1 << j)
                ]

                found[smiles] = (descriptors, groups)

        return found
