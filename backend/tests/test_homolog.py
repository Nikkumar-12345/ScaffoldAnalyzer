"""
Checks the homologous-protein lookup.

Run from the backend folder:

    PYTHONPATH=. python tests/test_homolog.py

If the precomputed cache is not installed the service reports itself
unavailable and the rest of the app is unaffected, which this prints
rather than treating as a failure.
"""

from app.services.homolog_service import HomologService


print("cache available:", HomologService.is_available())


if not HomologService.is_available():

    print(
        "No homolog cache installed - the Homologous Proteins panel "
        "will show an explanatory message and nothing else changes."
    )

else:

    # EGFR: its closest relatives are the other ErbB family members
    query = "P00533"

    protein = HomologService.get_protein(query)

    print("query:", protein)

    homologs = HomologService.get_homologs(query, limit=5)

    for hit in homologs:

        print(
            f"  {hit['uniprot_id']:8s} "
            f"{str(hit['target_name'])[:38]:38s} "
            f"identity={hit['identity']:5.1f}% "
            f"coverage={hit['coverage']:5.1f}% "
            f"E={hit['evalue']:.1e} "
            f"data={hit['has_activity_data']}"
        )

    assert homologs, "expected EGFR to have homologs"

    assert homologs[0]["identity"] > 40, (
        "expected the closest EGFR homolog to be clearly related"
    )

    erbb = {"P04626", "P21860", "Q15303"}

    found = {hit["uniprot_id"] for hit in homologs}

    assert erbb & found, (
        f"expected ErbB family members among the top hits, got {found}"
    )

    # Scores must come back in descending order of significance
    bits = [hit["bit_score"] for hit in homologs]

    assert bits == sorted(bits, reverse=True), (
        "homologs are not ordered by bit score"
    )

    # Benchmark flag must agree with the configured threshold
    threshold = HomologService.benchmark_threshold()

    basis = HomologService.benchmark_basis()

    print(f"benchmark: {threshold}% {basis}")

    for hit in homologs:

        expected = hit[basis] is not None and hit[basis] >= threshold

        assert hit["meets_benchmark"] is expected, (
            f"{hit['uniprot_id']} benchmark flag disagrees with "
            f"{basis}={hit[basis]} vs threshold {threshold}"
        )

    # An unknown accession must not raise
    assert HomologService.get_protein("NOT_AN_ID") is None

    assert HomologService.get_homologs("NOT_AN_ID") == []

    # The analysis block is always a dictionary
    summary = HomologService.summary_for_target(query)

    assert summary["available"] is True

    assert summary["homologs"], "expected homologs in the summary block"

    missing = HomologService.summary_for_target("NOT_AN_ID")

    assert missing["available"] is False

    assert missing["reason"]

    print("all homolog checks passed")
