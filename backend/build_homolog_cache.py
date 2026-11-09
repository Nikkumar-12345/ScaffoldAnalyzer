"""
Build the precomputed homologous-protein cache.

For every target in the local ChEMBL database this script:

    1. downloads the protein sequence from UniProt,
    2. runs an all-against-all Smith-Waterman local alignment
       (the same alignment BLAST approximates, but exact),
    3. stores the most similar proteins for each target together with
       percent identity, coverage, bit score and an estimated E-value.

The resulting database is read at runtime by HomologService, so no
alignment and no network access is needed when the app is serving
requests.

Requirements (build time only - NOT needed to run the app):

    pip install parasail

Usage (from the backend folder):

    python build_homolog_cache.py <path-to-chembl.db> [output.db]

Rebuild it whenever the ChEMBL database changes.
"""

import gzip
import math
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from multiprocessing import Pool
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.services.homolog_service import HomologService  # noqa: E402

DEFAULT_OUTPUT = BASE_DIR / "precomputed" / "homologs.db"

UNIPROT_BATCH_URL = (
    "https://rest.uniprot.org/uniprotkb/accessions"
    "?accessions={ids}&format=fasta"
)

# Accessions per request (UniProt allows up to 100)
BATCH_SIZE = 100

# How many homologs to keep per target
TOP_N = 50

# Alignment settings - BLOSUM62 with the standard BLAST gap penalties
GAP_OPEN = 11
GAP_EXTEND = 1

# Karlin-Altschul parameters published by NCBI for BLOSUM62 with
# gap open 11 / extend 1. Used to turn raw scores into bit scores and
# E-values comparable to BLAST output.
KA_LAMBDA = 0.267
KA_K = 0.041

# Only keep hits at least this significant
MAX_EVALUE = 1e-3


_SEQUENCES = None
_TOTAL_DB_LENGTH = 0


# ------------------------------------------------------------
# DOWNLOAD SEQUENCES
# ------------------------------------------------------------

def parse_fasta(text):
    """Yields (accession, sequence) from UniProt FASTA text."""

    accession = None
    chunks = []

    for line in text.splitlines():

        if line.startswith(">"):

            if accession is not None:
                yield accession, "".join(chunks)

            # >sp|P00533|EGFR_HUMAN Epidermal growth factor receptor ...
            parts = line[1:].split("|")

            accession = parts[1] if len(parts) > 2 else parts[0].split()[0]
            chunks = []

        elif accession is not None:

            chunks.append(line.strip())

    if accession is not None:
        yield accession, "".join(chunks)


def fetch_batch(accessions, attempts=4):

    url = UNIPROT_BATCH_URL.format(ids=",".join(accessions))

    for attempt in range(attempts):

        try:

            request = urllib.request.Request(
                url,
                headers={"User-Agent": "scaffold-analyzer-build"}
            )

            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read().decode("utf-8")

        except (urllib.error.URLError, TimeoutError) as error:

            if attempt == attempts - 1:
                print(f"  giving up on a batch: {error}")
                return ""

            time.sleep(2 ** attempt)

    return ""


def download_sequences(accessions):

    sequences = {}

    for start in range(0, len(accessions), BATCH_SIZE):

        batch = accessions[start:start + BATCH_SIZE]

        text = fetch_batch(batch)

        for accession, sequence in parse_fasta(text):

            if sequence:
                sequences[accession] = sequence

        done = min(start + BATCH_SIZE, len(accessions))

        if done % 1000 < BATCH_SIZE:
            print(f"  downloaded {done:,}/{len(accessions):,} "
                  f"({len(sequences):,} sequences)")

    return sequences


# ------------------------------------------------------------
# ALIGNMENT
# ------------------------------------------------------------

def bit_score(raw_score):

    return (KA_LAMBDA * raw_score - math.log(KA_K)) / math.log(2)


def e_value(raw_score, query_length, db_length):

    return (
        query_length
        * db_length
        * KA_K
        * math.exp(-KA_LAMBDA * raw_score)
    )


def init_worker(sequences, total_db_length):

    global _SEQUENCES, _TOTAL_DB_LENGTH

    _SEQUENCES = sequences
    _TOTAL_DB_LENGTH = total_db_length


def search_block(block):
    """
    Aligns each query in the block against every sequence and returns
    the most significant hits with identity and coverage.
    """

    import heapq

    import parasail

    matrix = parasail.blosum62

    results = []

    accessions = list(_SEQUENCES.keys())

    for query_accession in block:

        query = _SEQUENCES[query_accession]

        profile = parasail.profile_create_16(query, matrix)

        best = []

        for hit_accession in accessions:

            if hit_accession == query_accession:
                continue

            result = parasail.sw_striped_profile_16(
                profile,
                _SEQUENCES[hit_accession],
                GAP_OPEN,
                GAP_EXTEND
            )

            score = result.score

            # Keep a running top-N by raw score
            if len(best) < TOP_N:
                heapq.heappush(best, (score, hit_accession))
            elif score > best[0][0]:
                heapq.heapreplace(best, (score, hit_accession))

        # Second pass: traceback only for the hits we keep, so that
        # identity and coverage are exact.
        hits = []

        for score, hit_accession in best:

            evalue = e_value(score, len(query), _TOTAL_DB_LENGTH)

            if evalue > MAX_EVALUE:
                continue

            traced = parasail.sw_trace_striped_16(
                query,
                _SEQUENCES[hit_accession],
                GAP_OPEN,
                GAP_EXTEND,
                matrix
            )

            alignment = traced.traceback

            aligned_query = alignment.query
            aligned_ref = alignment.ref
            comparison = alignment.comp

            aligned_length = len(aligned_query)

            if aligned_length == 0:
                continue

            identical = sum(
                1
                for a, b in zip(aligned_query, aligned_ref)
                if a == b and a != "-"
            )

            positives = sum(
                1
                for c in comparison
                if c in ("|", ":")
            )

            ungapped_query = sum(
                1 for a in aligned_query if a != "-"
            )

            hits.append((
                query_accession,
                hit_accession,
                round(100.0 * identical / aligned_length, 2),
                round(100.0 * positives / aligned_length, 2),
                round(100.0 * ungapped_query / len(query), 2),
                round(bit_score(score), 1),
                evalue,
                aligned_length,
            ))

        results.extend(hits)

    return results


def blocks(items, size):

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

    # --------------------------------------------------
    # TARGETS
    # --------------------------------------------------

    print(f"Reading targets from {chembl_db} ...")

    src = sqlite3.connect(str(chembl_db))

    targets = src.execute(
        "SELECT uniprot_id, target_chembl_id, target_name, organism "
        "FROM targets WHERE uniprot_id IS NOT NULL AND uniprot_id != ''"
    ).fetchall()

    activity_counts = dict(
        src.execute(
            "SELECT t.uniprot_id, COUNT(DISTINCT a.molecule_chembl_id) "
            "FROM targets t "
            "JOIN activities a "
            "  ON a.target_chembl_id = t.target_chembl_id "
            "WHERE t.uniprot_id IS NOT NULL "
            "GROUP BY t.uniprot_id"
        )
    )

    src.close()

    print(f"Targets with a UniProt ID: {len(targets):,}")
    print(f"Targets with activity data: {len(activity_counts):,}")

    # --------------------------------------------------
    # SEQUENCES
    # --------------------------------------------------

    accessions = sorted({row[0] for row in targets})

    print(f"Downloading {len(accessions):,} sequences from UniProt ...")

    sequences = download_sequences(accessions)

    print(f"Sequences retrieved: {len(sequences):,} "
          f"({len(accessions) - len(sequences):,} not found)")

    if not sequences:
        raise SystemExit(
            "No sequences could be downloaded - check network access."
        )

    total_db_length = sum(len(s) for s in sequences.values())

    # --------------------------------------------------
    # OUTPUT SCHEMA
    # --------------------------------------------------

    out = sqlite3.connect(str(tmp))
    HomologService.create_schema(out)

    rows = []

    for uniprot_id, chembl_id, name, organism in targets:

        sequence = sequences.get(uniprot_id)

        rows.append((
            uniprot_id,
            chembl_id,
            name,
            organism,
            len(sequence) if sequence else None,
            sequence,
            1 if uniprot_id in activity_counts else 0,
            activity_counts.get(uniprot_id, 0),
        ))

    out.executemany(
        "INSERT OR REPLACE INTO proteins "
        "(uniprot_id, target_chembl_id, target_name, organism, "
        "length, sequence, has_activity_data, molecule_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )

    out.commit()

    # --------------------------------------------------
    # ALL-AGAINST-ALL SEARCH
    # --------------------------------------------------

    searchable = sorted(sequences)

    workers = max(1, os.cpu_count() or 1)

    print(f"Aligning {len(searchable):,} x {len(searchable):,} "
          f"sequences on {workers} process(es) ...")

    start = time.time()
    done = 0
    stored = 0

    with Pool(
        workers,
        initializer=init_worker,
        initargs=(sequences, total_db_length)
    ) as pool:

        for hits in pool.imap_unordered(
            search_block,
            blocks(searchable, 20)
        ):

            out.executemany(
                "INSERT OR REPLACE INTO homologs "
                "(query_uniprot, hit_uniprot, identity, similarity, "
                "coverage, bit_score, evalue, aligned_length) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                hits
            )

            stored += len(hits)
            done += 20

            if done % 200 < 20:

                elapsed = time.time() - start
                rate = done / max(elapsed, 1e-6)
                remaining = (len(searchable) - done) / max(rate, 1e-6)

                print(f"  {min(done, len(searchable)):,}/"
                      f"{len(searchable):,} queries, "
                      f"{stored:,} hits, "
                      f"~{remaining / 60:.0f} min left")

        out.commit()

    # --------------------------------------------------
    # FINISH
    # --------------------------------------------------

    out.executemany(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        [
            ("schema_version", str(HomologService.SCHEMA_VERSION)),
            ("total_db_length", str(total_db_length)),
            ("sequence_count", str(len(sequences))),
            ("ka_lambda", str(KA_LAMBDA)),
            ("ka_k", str(KA_K)),
            ("gap_open", str(GAP_OPEN)),
            ("gap_extend", str(GAP_EXTEND)),
            ("top_n", str(TOP_N)),
            ("max_evalue", str(MAX_EVALUE)),
        ]
    )

    out.commit()
    out.execute("VACUUM")
    out.close()

    tmp.replace(output)

    print(f"Done: {output} ({output.stat().st_size / 1e6:.1f} MB), "
          f"{stored:,} homolog pairs")

    with open(output, "rb") as src_file, \
            gzip.open(str(output) + ".gz", "wb", compresslevel=6) as dst:

        while True:

            chunk = src_file.read(4 * 1024 * 1024)

            if not chunk:
                break

            dst.write(chunk)

    gz_size = Path(str(output) + ".gz").stat().st_size / 1e6

    print(f"Compressed: {output}.gz ({gz_size:.1f} MB)")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    build(
        sys.argv[1],
        sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT,
    )
