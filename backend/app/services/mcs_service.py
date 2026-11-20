"""
Chemical series clustering and Maximum Common Substructure extraction.

A Murcko scaffold is an exact match: two molecules either reduce to the
same scaffold or they do not. That is strict. Two compounds can share an
obvious common core and still land in different scaffold groups because
one of them carries an extra ring.

This module takes the complementary view. The active molecules of a
target are clustered into chemical series by structural similarity, and
the largest substructure common to each series is then extracted. The
result is the shared core of a series as a medicinal chemist would draw
it, rather than the core that the Murcko definition happens to produce.

Pipeline (following Dalke/Bemis-Murcko practice and the ChEMBL series
workflow):

    molecules
        -> Morgan fingerprints
        -> Taylor-Butina clustering on Tanimoto distance
        -> one chemical series per cluster
        -> rdFMCS.FindMCS per series
        -> MCS as SMARTS, with coverage and activity statistics
"""

import csv

from rdkit import Chem, DataStructs
from rdkit.Chem import rdFMCS, rdFingerprintGenerator
from rdkit.Chem.Draw import rdMolDraw2D
from rdkit.Chem.Scaffolds import MurckoScaffold


class MCSService:

    # -----------------------------------------
    # SETTINGS
    # -----------------------------------------

    # Tanimoto similarity above which two molecules are neighbours.
    # 0.6 on Morgan/ECFP4 is the usual cut for "same series".
    SIMILARITY_CUTOFF = 0.6

    # Minimum series size to report. 1 reports every cluster, including
    # molecules that ended up on their own, which is what a full
    # per-series export expects.
    MIN_SERIES_SIZE = 1

    # Clustering compares every molecule with every other, so it grows
    # quadratically. Above this count only the most potent molecules are
    # clustered, and the number actually used is reported in the result.
    MAX_MOLECULES = 12000

    # FindMCS is NP-hard. It is run on a sample of each series and given
    # a time limit; if it runs out of time RDKit returns the best common
    # substructure found so far, which is flagged in the output.
    MCS_SAMPLE_SIZE = 20
    MCS_TIMEOUT_SECONDS = 3

    # Fraction of the sampled molecules that must contain the
    # substructure. 1.0 is the classical definition - the core must be
    # present in every molecule - and is both stricter and considerably
    # faster to search than a partial threshold.
    MCS_THRESHOLD = 1.0

    # Fingerprint settings
    FP_RADIUS = 2
    FP_BITS = 2048

    # mcs_status values
    STATUS_SUCCESS = "success"
    STATUS_TIMEOUT = "timeout"
    STATUS_SINGLE = "single_molecule_series"
    STATUS_FAILED = "failed"

    _generator = None

    # -----------------------------------------
    # FINGERPRINTS
    # -----------------------------------------

    @classmethod
    def generator(cls):

        if cls._generator is None:

            cls._generator = (
                rdFingerprintGenerator.GetMorganGenerator(
                    radius=cls.FP_RADIUS,
                    fpSize=cls.FP_BITS
                )
            )

        return cls._generator

    @classmethod
    def build_fingerprints(cls, molecules):
        """
        Returns (kept_molecules, fingerprints, parsed_molecules) for the
        molecules whose SMILES RDKit can parse. Unparseable entries are
        dropped.

        Parsing a SMILES string is the single most repeated cost in this
        module, so each molecule is parsed exactly once here and the
        parsed object is reused for clustering, for the MCS search, for
        the coverage check and for drawing.
        """

        generator = cls.generator()

        kept = []
        fingerprints = []
        parsed = []

        for molecule in molecules:

            smiles = molecule.get("smiles")

            if not smiles:
                continue

            mol = Chem.MolFromSmiles(smiles)

            if mol is None:
                continue

            kept.append(molecule)
            parsed.append(mol)

            fingerprints.append(
                generator.GetFingerprint(mol)
            )

        return kept, fingerprints, parsed

    # -----------------------------------------
    # TAYLOR-BUTINA CLUSTERING
    # -----------------------------------------

    @classmethod
    def cluster(cls, fingerprints, cutoff=None):
        """
        Taylor-Butina clustering.

        The molecule with the most neighbours becomes the centroid of a
        cluster and claims all of its unassigned neighbours; the process
        repeats on what is left. Molecules with no neighbours end up in
        clusters of their own.

        Similarities are computed one row at a time rather than as a
        full distance matrix, so memory stays proportional to the number
        of neighbours actually found instead of to the square of the
        number of molecules.

        Returns a list of clusters, each a list of indices, centroid
        first, ordered largest cluster first.
        """

        if cutoff is None:
            cutoff = cls.SIMILARITY_CUTOFF

        total = len(fingerprints)

        if total == 0:
            return []

        neighbours = []

        for index in range(total):

            similarities = DataStructs.BulkTanimotoSimilarity(
                fingerprints[index],
                fingerprints
            )

            neighbours.append([
                other
                for other, value in enumerate(similarities)
                if value >= cutoff and other != index
            ])

        # Most connected molecules first
        order = sorted(
            range(total),
            key=lambda index: len(neighbours[index]),
            reverse=True
        )

        assigned = [False] * total

        clusters = []

        for index in order:

            if assigned[index]:
                continue

            members = [index]

            assigned[index] = True

            for other in neighbours[index]:

                if not assigned[other]:

                    members.append(other)

                    assigned[other] = True

            clusters.append(members)

        clusters.sort(key=len, reverse=True)

        return clusters

    # -----------------------------------------
    # MAXIMUM COMMON SUBSTRUCTURE
    # -----------------------------------------

    @classmethod
    def find_mcs(cls, mols, timeout=None, threshold=None):
        """
        Returns the maximum common substructure of the given molecules.

        completeRingsOnly and ringMatchesRingOnly keep the result
        chemically meaningful: a ring is either matched whole or not at
        all, and a ring atom never matches a chain atom. Without them
        the MCS tends to be a chemically meaningless fragment of a ring.
        """

        if timeout is None:
            timeout = cls.MCS_TIMEOUT_SECONDS

        if threshold is None:
            threshold = cls.MCS_THRESHOLD

        if len(mols) < 2:
            return None

        try:

            result = rdFMCS.FindMCS(
                mols,
                timeout=timeout,
                threshold=threshold,
                ringMatchesRingOnly=True,
                completeRingsOnly=True,
                matchValences=False,
                atomCompare=rdFMCS.AtomCompare.CompareElements,
                bondCompare=rdFMCS.BondCompare.CompareOrder
            )

        except Exception as error:

            print(f"MCS search failed: {error}")

            return None

        if not result.smartsString:
            return None

        return {
            "smarts": result.smartsString,
            "num_atoms": result.numAtoms,
            "num_bonds": result.numBonds,
            "timed_out": bool(result.canceled)
        }

    @staticmethod
    def coverage(smarts, mols):
        """
        Percentage of the series that actually contains the MCS.

        With a threshold below 1.0 the MCS need only be present in most
        of the sampled molecules, so this reports how general it really
        is across the whole series.
        """

        pattern = Chem.MolFromSmarts(smarts)

        if pattern is None:
            return None

        matched = 0
        checked = 0

        for mol in mols:

            if mol is None:
                continue

            checked += 1

            if mol.HasSubstructMatch(pattern):
                matched += 1

        if checked == 0:
            return None

        return round(100.0 * matched / checked, 2)

    # -----------------------------------------
    # DRAWING
    # -----------------------------------------

    @staticmethod
    def draw_mcs(smarts, width=300, height=220):
        """Draws the common substructure on its own."""

        pattern = Chem.MolFromSmarts(smarts)

        if pattern is None:
            return None

        try:

            drawer = rdMolDraw2D.MolDraw2DSVG(width, height)

            rdMolDraw2D.PrepareAndDrawMolecule(drawer, pattern)

            drawer.FinishDrawing()

            return drawer.GetDrawingText()

        except Exception:

            return None

    @staticmethod
    def draw_with_highlight(mol, smarts, width=300, height=220):
        """
        Draws a molecule with the common substructure highlighted, which
        is how a shared core is normally presented.
        """

        pattern = Chem.MolFromSmarts(smarts) if smarts else None

        if mol is None:
            return None

        highlight_atoms = []
        highlight_bonds = []

        if pattern is not None:

            match = mol.GetSubstructMatch(pattern)

            if match:

                highlight_atoms = list(match)

                lookup = set(match)

                for bond in mol.GetBonds():

                    if (
                        bond.GetBeginAtomIdx() in lookup
                        and bond.GetEndAtomIdx() in lookup
                    ):
                        highlight_bonds.append(bond.GetIdx())

        try:

            drawer = rdMolDraw2D.MolDraw2DSVG(width, height)

            rdMolDraw2D.PrepareAndDrawMolecule(
                drawer,
                mol,
                highlightAtoms=highlight_atoms,
                highlightBonds=highlight_bonds
            )

            drawer.FinishDrawing()

            return drawer.GetDrawingText()

        except Exception:

            return None

    # -----------------------------------------
    # STATISTICS
    # -----------------------------------------

    @staticmethod
    def activity_stats(values):

        clean = [v for v in values if v is not None]

        if not clean:

            return {
                "count": 0,
                "max_pic50": None,
                "min_pic50": None,
                "median_pic50": None,
                "range_pic50": None
            }

        clean.sort()

        middle = len(clean) // 2

        if len(clean) % 2:
            median = clean[middle]
        else:
            median = (clean[middle - 1] + clean[middle]) / 2.0

        return {
            "count": len(clean),
            "max_pic50": round(clean[-1], 3),
            "min_pic50": round(clean[0], 3),
            "median_pic50": round(median, 3),
            "range_pic50": round(clean[-1] - clean[0], 3)
        }

    # -----------------------------------------
    # MURCKO SCAFFOLD COUNT PER SERIES
    # -----------------------------------------

    @staticmethod
    def count_scaffolds(mols):
        """
        Number of distinct Bemis-Murcko scaffolds inside a series.

        This is the figure that shows why the maximum common
        substructure is worth computing at all. A chemical series is
        built from overall structural similarity, so it routinely
        contains molecules whose Murcko scaffolds differ - one carries
        an extra ring, another closes a ring the rest leave open. The
        scaffold grouping would split them apart; the MCS recovers the
        core they genuinely share.
        """

        scaffolds = set()

        for mol in mols:

            if mol is None:
                continue

            try:

                scaffold = MurckoScaffold.GetScaffoldForMol(mol)

            except Exception:

                continue

            if scaffold is None or scaffold.GetNumAtoms() == 0:
                continue

            smiles = Chem.MolToSmiles(scaffold, canonical=True)

            if smiles:
                scaffolds.add(smiles)

        return len(scaffolds)

    # -----------------------------------------
    # MAIN ANALYSIS
    # -----------------------------------------

    @classmethod
    def analyze(
        cls,
        molecules,
        similarity_cutoff=None,
        min_series_size=None,
        detail_limit=25,
        draw=True,
        progress=None
    ):
        """
        Clusters a target's molecules into chemical series and extracts
        the maximum common substructure of each.

        molecules:       [{"chembl_id", "smiles", "pic50"}, ...]
        detail_limit:    how many of the largest series carry their full
                         molecule list and structure images. Every
                         series is still reported with its size,
                         scaffold count and MCS; this only bounds the
                         size of the result.

        Series are numbered SERIES_0001 upwards, largest first.
        """

        def report(fraction, message):
            if progress is not None:
                progress(min(max(fraction, 0.0), 1.0), message)

        if similarity_cutoff is None:
            similarity_cutoff = cls.SIMILARITY_CUTOFF

        if min_series_size is None:
            min_series_size = cls.MIN_SERIES_SIZE

        total_supplied = len(molecules)

        # ----------------------------------------
        # Cap the molecule count, most potent first
        # ----------------------------------------

        working = list(molecules)

        truncated = False

        if len(working) > cls.MAX_MOLECULES:

            working.sort(
                key=lambda m: (
                    m.get("pic50")
                    if m.get("pic50") is not None
                    else -1
                ),
                reverse=True
            )

            working = working[:cls.MAX_MOLECULES]

            truncated = True

        report(0.05, "Generating fingerprints")

        kept, fingerprints, parsed = cls.build_fingerprints(working)

        if len(kept) < 2:

            return {
                "available": False,
                "reason": (
                    "At least two valid molecules are required to form "
                    f"a chemical series (found {len(kept)})."
                ),
                "parameters": cls.parameters(
                    similarity_cutoff,
                    min_series_size
                ),
                "summary": None,
                "series": []
            }

        report(0.15, f"Clustering {len(kept):,} molecules into series")

        clusters = cls.cluster(fingerprints, similarity_cutoff)

        reported = [
            c for c in clusters
            if len(c) >= min_series_size
        ]

        singletons = sum(1 for c in clusters if len(c) == 1)

        # ----------------------------------------
        # MCS per series
        # ----------------------------------------

        series = []

        timeouts = 0
        successes = 0

        for position, members in enumerate(reported):

            if position % 10 == 0:
                report(
                    0.2 + 0.78 * position / max(len(reported), 1),
                    f"Extracting common substructure "
                    f"({position + 1:,}/{len(reported):,} series)"
                )

            entries = [kept[i] for i in members]

            series_mols = [parsed[i] for i in members]

            detailed = position < detail_limit

            record = {
                "chemical_series_id": f"SERIES_{position + 1:04d}",
                "id": position + 1,
                "number_of_molecules": len(entries),
                "scaffolds_in_series": cls.count_scaffolds(series_mols),
                "mcs_status": None,
                "mcs_smarts": None,
                "mcs_atoms": None,
                "mcs_bonds": None,
                "mcs_coverage": None,
                "mcs_svg": None,
                "representative_svg": None,
                "representative": {
                    "chembl_id": entries[0].get("chembl_id"),
                    "smiles": entries[0].get("smiles"),
                    "pic50": entries[0].get("pic50")
                },
                "activity": cls.activity_stats(
                    [e.get("pic50") for e in entries]
                ),
                "molecules": [
                    {
                        "chembl_id": e.get("chembl_id"),
                        "smiles": e.get("smiles"),
                        "pic50": e.get("pic50")
                    }
                    for e in entries
                ] if detailed else []
            }

            # ------------------------------------
            # A single molecule has no common
            # substructure to speak of
            # ------------------------------------

            if len(series_mols) < 2:

                record["mcs_status"] = cls.STATUS_SINGLE

                series.append(record)

                continue

            # Sample the most potent members, so a very large series
            # stays tractable.
            ranked = sorted(
                range(len(members)),
                key=lambda index: (
                    entries[index].get("pic50")
                    if entries[index].get("pic50") is not None
                    else -1
                ),
                reverse=True
            )[:cls.MCS_SAMPLE_SIZE]

            mcs = cls.find_mcs(
                [series_mols[index] for index in ranked]
            )

            if mcs is None:

                record["mcs_status"] = cls.STATUS_FAILED

                series.append(record)

                continue

            record["mcs_smarts"] = mcs["smarts"]
            record["mcs_atoms"] = mcs["num_atoms"]
            record["mcs_bonds"] = mcs["num_bonds"]

            if mcs["timed_out"]:
                record["mcs_status"] = cls.STATUS_TIMEOUT
                timeouts += 1
            else:
                record["mcs_status"] = cls.STATUS_SUCCESS
                successes += 1

            if detailed:

                record["mcs_coverage"] = cls.coverage(
                    mcs["smarts"],
                    series_mols
                )

                if draw:

                    record["mcs_svg"] = cls.draw_mcs(
                        mcs["smarts"]
                    )

                    record["representative_svg"] = (
                        cls.draw_with_highlight(
                            series_mols[0],
                            mcs["smarts"]
                        )
                    )

            series.append(record)

        report(1.0, "Chemical series complete")

        return {
            "available": True,
            "reason": None,
            "parameters": cls.parameters(
                similarity_cutoff,
                min_series_size
            ),
            "summary": {
                "molecules_supplied": total_supplied,
                "molecules_clustered": len(kept),
                "truncated": truncated,
                "series_total": len(clusters),
                "series_reported": len(series),
                "singletons": singletons,
                "mcs_success": successes,
                "mcs_timeout": timeouts,
                "largest_series": (
                    series[0]["number_of_molecules"] if series else 0
                )
            },
            "series": series
        }

    @classmethod
    def parameters(cls, similarity_cutoff, min_series_size):

        return {
            "similarity_cutoff": similarity_cutoff,
            "min_series_size": min_series_size,
            "fingerprint": (
                f"Morgan radius {cls.FP_RADIUS}, {cls.FP_BITS} bits"
            ),
            "clustering": "Taylor-Butina on Tanimoto distance",
            "mcs_threshold": cls.MCS_THRESHOLD,
            "mcs_timeout_seconds": cls.MCS_TIMEOUT_SECONDS,
            "mcs_sample_size": cls.MCS_SAMPLE_SIZE,
            "max_molecules": cls.MAX_MOLECULES
        }

    # -----------------------------------------
    # CSV EXPORT
    # -----------------------------------------

    CSV_COLUMNS = [
        "target_chembl_id",
        "target_name",
        "uniprot_id",
        "chemical_series_id",
        "number_of_molecules",
        "scaffolds_in_series",
        "mcs_status",
        "mcs_smarts",
        "mcs_atoms",
        "mcs_bonds",
    ]

    @classmethod
    def to_csv(cls, result, target_chembl_id, target_name, uniprot_id,
               handle):
        """
        Writes one row per chemical series, in the per-series export
        format: target identifiers, series identifier, how many
        molecules and distinct Murcko scaffolds it contains, and the
        maximum common substructure found for it.
        """

        writer = csv.writer(handle)

        writer.writerow(cls.CSV_COLUMNS)

        for entry in result.get("series", []):

            writer.writerow([
                target_chembl_id,
                target_name,
                uniprot_id,
                entry["chemical_series_id"],
                entry["number_of_molecules"],
                entry["scaffolds_in_series"],
                entry["mcs_status"],
                entry["mcs_smarts"] or "",
                entry["mcs_atoms"] if entry["mcs_atoms"] is not None else "",
                entry["mcs_bonds"] if entry["mcs_bonds"] is not None else "",
            ])
