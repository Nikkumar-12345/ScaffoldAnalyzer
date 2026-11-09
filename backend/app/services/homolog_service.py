"""
Homologous-protein lookup (see build_homolog_cache.py).

Every target in the local ChEMBL database was aligned against every
other target with a Smith-Waterman local alignment using BLOSUM62 and
the standard BLAST gap penalties. The most significant hits are stored
here together with percent identity, coverage, bit score and an
estimated E-value, so a homology search at runtime is a plain database
lookup - no alignment and no network access.

If the cache file is missing the service reports itself unavailable and
the rest of the application carries on exactly as before.
"""

import gzip
import os
import shutil
import sqlite3
import threading
from pathlib import Path


class HomologService:

    SCHEMA_VERSION = 1

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    DEFAULT_PATH = BASE_DIR / "precomputed" / "homologs.db"

    # Shown with the results so the numbers can be interpreted
    METHOD = (
        "Smith-Waterman local alignment (BLOSUM62, gap open 11, "
        "extend 1). E-values are estimated with the standard "
        "Karlin-Altschul parameters for this scoring scheme."
    )

    # The cutoff at which a hit is treated as a meaningful homolog.
    # Hits below it are still listed - they are simply not marked as
    # meeting the benchmark - so nothing is hidden from the user.
    #
    #   HOMOLOG_BENCHMARK        percentage, default 70
    #   HOMOLOG_BENCHMARK_BASIS  "similarity" (identical plus
    #                            conservative substitutions, the usual
    #                            reading of a "70% similarity"
    #                            benchmark) or "identity" (identical
    #                            residues only, a stricter test)

    # Sensible limits for a "how similar counts as homologous?"
    # control, and what each band means.
    #
    # Identity bands follow the usual reading of sequence comparison:
    # below roughly 25% identity ("the twilight zone") sequence alone
    # cannot establish homology reliably, 25-40% indicates a shared
    # fold or superfamily, 40-70% the same family, and above 70% close
    # relatives such as orthologs in another species.
    #
    # Similarity (identical plus conservative substitutions) always
    # scores higher than identity, so its bands sit higher.

    BANDS = {

        "identity": {
            "min": 20,
            "max": 95,
            "zones": [
                {"from": 20, "to": 25, "label": "Twilight zone",
                 "note": "Sequence alone cannot confirm homology here."},
                {"from": 25, "to": 40, "label": "Probable homolog",
                 "note": "Usually a shared fold or superfamily."},
                {"from": 40, "to": 70, "label": "Same family",
                 "note": "Clearly related; binding sites often similar."},
                {"from": 70, "to": 101, "label": "Close relative",
                 "note": "Orthologs or very close paralogs."},
            ],
        },

        "similarity": {
            "min": 40,
            "max": 95,
            "zones": [
                {"from": 40, "to": 50, "label": "Twilight zone",
                 "note": "Sequence alone cannot confirm homology here."},
                {"from": 50, "to": 65, "label": "Probable homolog",
                 "note": "Usually a shared fold or superfamily."},
                {"from": 65, "to": 80, "label": "Same family",
                 "note": "Clearly related; binding sites often similar."},
                {"from": 80, "to": 101, "label": "Close relative",
                 "note": "Orthologs or very close paralogs."},
            ],
        },

    }

    @classmethod
    def bands(cls, basis=None):

        return cls.BANDS[basis or cls.benchmark_basis()]

    @classmethod
    def benchmark_threshold(cls):

        try:
            return float(os.getenv("HOMOLOG_BENCHMARK", "70"))
        except ValueError:
            return 70.0

    @classmethod
    def benchmark_basis(cls):

        basis = os.getenv(
            "HOMOLOG_BENCHMARK_BASIS",
            "similarity"
        ).strip().lower()

        return basis if basis in ("similarity", "identity") else "similarity"

    @classmethod
    def benchmark_info(cls):
        """The cutoff settings the UI needs to render its control."""

        return {
            "threshold": cls.benchmark_threshold(),
            "basis": cls.benchmark_basis(),
            "bands": cls.BANDS,
        }

    @classmethod
    def meets_benchmark(cls, hit):

        value = hit.get(cls.benchmark_basis())

        if value is None:
            return False

        return value >= cls.benchmark_threshold()

    _lock = threading.Lock()
    _local = threading.local()
    _available = None
    _path = None
    _meta = {}

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

            CREATE TABLE IF NOT EXISTS proteins (
                uniprot_id TEXT PRIMARY KEY,
                target_chembl_id TEXT,
                target_name TEXT,
                organism TEXT,
                length INTEGER,
                sequence TEXT,
                has_activity_data INTEGER NOT NULL DEFAULT 0,
                molecule_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS homologs (
                query_uniprot TEXT NOT NULL,
                hit_uniprot TEXT NOT NULL,
                identity REAL NOT NULL,
                similarity REAL,
                coverage REAL,
                bit_score REAL NOT NULL,
                evalue REAL NOT NULL,
                aligned_length INTEGER,
                PRIMARY KEY (query_uniprot, hit_uniprot)
            );

            CREATE INDEX IF NOT EXISTS idx_homologs_query
                ON homologs (query_uniprot, bit_score DESC);
            """
        )

    # --------------------------------------------------
    # LOCATE / OPEN
    # --------------------------------------------------

    @classmethod
    def get_path(cls):

        env_path = os.getenv("HOMOLOG_DB_PATH")

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
                    print(f"Homolog cache not found at {path}; "
                          "homologous-protein analysis is disabled.")
                    cls._available = False
                    return False

                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)

                meta = dict(conn.execute("SELECT key, value FROM meta"))
                conn.close()

                if meta.get("schema_version") != str(cls.SCHEMA_VERSION):
                    print("Homolog cache schema mismatch; ignoring it.")
                    cls._available = False
                    return False

                cls._meta = meta
                cls._path = path
                cls._available = True

                print(f"Using homolog cache: {path} "
                      f"({meta.get('sequence_count', '?')} proteins)")

            except Exception as error:

                print(f"Could not open homolog cache: {error}")
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
    def get_protein(cls, uniprot_id):

        if not cls.is_available() or not uniprot_id:
            return None

        row = cls._conn().execute(
            "SELECT uniprot_id, target_chembl_id, target_name, organism, "
            "length, has_activity_data, molecule_count "
            "FROM proteins WHERE uniprot_id = ?",
            (uniprot_id.strip().upper(),)
        ).fetchone()

        if row is None:
            return None

        return {
            "uniprot_id": row[0],
            "target_chembl_id": row[1],
            "target_name": row[2],
            "organism": row[3],
            "length": row[4],
            "has_activity_data": bool(row[5]),
            "molecule_count": row[6],
        }

    @classmethod
    def get_homologs(
        cls,
        uniprot_id,
        limit=25,
        min_identity=0.0,
        min_similarity=0.0,
        with_data_only=False
    ):
        """
        Returns the proteins most similar in sequence to uniprot_id,
        most significant first.
        """

        if not cls.is_available() or not uniprot_id:
            return []

        query = """
            SELECT
                h.hit_uniprot,
                h.identity,
                h.similarity,
                h.coverage,
                h.bit_score,
                h.evalue,
                h.aligned_length,
                p.target_chembl_id,
                p.target_name,
                p.organism,
                p.length,
                p.has_activity_data,
                p.molecule_count
            FROM homologs h
            LEFT JOIN proteins p ON p.uniprot_id = h.hit_uniprot
            WHERE h.query_uniprot = ?
              AND h.identity >= ?
        """

        params = [uniprot_id.strip().upper(), float(min_identity)]

        if min_similarity:
            query += " AND h.similarity >= ?"
            params.append(float(min_similarity))

        if with_data_only:
            query += " AND p.has_activity_data = 1"

        query += " ORDER BY h.bit_score DESC LIMIT ?"

        params.append(int(limit))

        hits = [
            {
                "uniprot_id": row[0],
                "identity": row[1],
                "similarity": row[2],
                "coverage": row[3],
                "bit_score": row[4],
                "evalue": row[5],
                "aligned_length": row[6],
                "target_chembl_id": row[7],
                "target_name": row[8],
                "organism": row[9],
                "length": row[10],
                "has_activity_data": bool(row[11]),
                "molecule_count": row[12] or 0,
            }
            for row in cls._conn().execute(query, params)
        ]

        for hit in hits:
            hit["meets_benchmark"] = cls.meets_benchmark(hit)

        return hits

    @classmethod
    def identity_map(cls, uniprot_id, hit_uniprot_ids):
        """
        {hit uniprot id: identity} for the hits that are significant
        homologs of uniprot_id. Used to annotate cross-target results.
        """

        if not cls.is_available() or not uniprot_id or not hit_uniprot_ids:
            return {}

        wanted = [h for h in set(hit_uniprot_ids) if h]

        if not wanted:
            return {}

        found = {}
        conn = cls._conn()
        query_id = uniprot_id.strip().upper()

        for i in range(0, len(wanted), 900):

            chunk = wanted[i:i + 900]
            marks = ",".join("?" * len(chunk))

            for hit, identity, similarity, bits, evalue in conn.execute(
                "SELECT hit_uniprot, identity, similarity, bit_score, "
                "evalue FROM homologs WHERE query_uniprot = ? "
                f"AND hit_uniprot IN ({marks})",
                [query_id, *chunk]
            ):

                entry = {
                    "identity": identity,
                    "similarity": similarity,
                    "bit_score": bits,
                    "evalue": evalue,
                }

                entry["meets_benchmark"] = cls.meets_benchmark(entry)

                found[hit] = entry

        return found

    @classmethod
    def summary_for_target(cls, uniprot_id, limit=50):
        """
        The block attached to an analysis result. Always returns a
        dictionary so the frontend can render a consistent panel.
        """

        if not cls.is_available():

            return {
                "available": False,
                "reason": (
                    "Homologous-protein data is not installed on this "
                    "server."
                ),
                "method": cls.METHOD,
                "benchmark": {
                    "threshold": cls.benchmark_threshold(),
                    "basis": cls.benchmark_basis(),
                    "passing": 0,
                    "bands": cls.BANDS,
                },
                "query": None,
                "homologs": [],
            }

        protein = cls.get_protein(uniprot_id)

        if protein is None:

            return {
                "available": False,
                "reason": (
                    f"'{uniprot_id}' is not one of the proteins in the "
                    "local ChEMBL database, so no homology search has "
                    "been precomputed for it."
                ),
                "method": cls.METHOD,
                "benchmark": {
                    "threshold": cls.benchmark_threshold(),
                    "basis": cls.benchmark_basis(),
                    "passing": 0,
                    "bands": cls.BANDS,
                },
                "query": None,
                "homologs": [],
            }

        if not protein.get("length"):

            return {
                "available": False,
                "reason": (
                    f"No protein sequence is on record for "
                    f"'{uniprot_id}', so it could not be compared "
                    "against the other proteins."
                ),
                "method": cls.METHOD,
                "benchmark": {
                    "threshold": cls.benchmark_threshold(),
                    "basis": cls.benchmark_basis(),
                    "passing": 0,
                    "bands": cls.BANDS,
                },
                "query": protein,
                "homologs": [],
            }

        homologs = cls.get_homologs(uniprot_id, limit=limit)

        return {
            "available": True,
            "reason": None,
            "method": cls.METHOD,
            "query": protein,
            "total": len(homologs),
            "with_activity_data": sum(
                1 for h in homologs if h["has_activity_data"]
            ),
            "benchmark": {
                "threshold": cls.benchmark_threshold(),
                "basis": cls.benchmark_basis(),
                "passing": sum(
                    1 for h in homologs if h["meets_benchmark"]
                ),
                "bands": cls.BANDS,
            },
            "homologs": homologs,
        }
