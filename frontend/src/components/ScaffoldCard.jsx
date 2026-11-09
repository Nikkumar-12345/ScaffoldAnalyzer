import { useState } from "react";
import api, { getErrorMessage } from "../services/api";
import { formatEvalue } from "../utils/format";

export default function ScaffoldCard({
    scaffold,
    onInvestigate,
    currentTarget,
    queryUniprot,
    homologFilter
}) {

    const descriptors = scaffold.descriptors || {};
    const drug = scaffold.druglikeness || {};
    const ranking = scaffold.ranking || {};

    const [otherTargets, setOtherTargets] = useState([]);
    const [loadingTargets, setLoadingTargets] = useState(false);
    const [showTargets, setShowTargets] = useState(false);
    const [showAllTargets, setShowAllTargets] = useState(false);
    const [targetSearch, setTargetSearch] = useState("");
    const [targetError, setTargetError] = useState("");
    const [homologCount, setHomologCount] = useState(0);
    const [benchmarkCount, setBenchmarkCount] = useState(0);
    const [benchmark, setBenchmark] = useState(null);

    async function findOtherTargets() {

        // If already loaded, just show the section
        if (otherTargets.length > 0) {

            setShowTargets(true);

            return;
        }

        setLoadingTargets(true);
        setTargetError("");

        try {

            const response = await api.post(
                "/scaffold/cross-targets",
                {

                    scaffold_smiles:
                        scaffold.scaffold_smiles,

                    current_target_chembl_id:
                        typeof currentTarget === "object"
                            ? currentTarget?.target_chembl_id
                            : currentTarget,

                    // Lets the server mark which of these targets
                    // are sequence homologs of the analysed protein.
                    query_uniprot_id: queryUniprot

                }
            );

            const data = response.data;

            // Homologous targets first, most similar at the top,
            // then everything else by molecule count as before.
            const sorted = [...(data.targets || [])].sort(
                (a, b) =>
                    (b.identity ?? -1) - (a.identity ?? -1)
            );

            setOtherTargets(sorted);

            setHomologCount(data.homologous_count ?? 0);

            setBenchmarkCount(data.benchmark_count ?? 0);

            setBenchmark(data.benchmark || null);

            setShowTargets(true);

        } catch (error) {

            console.error(
                "Cross-target error:",
                error
            );

            setTargetError(
                getErrorMessage(
                    error,
                    "Could not load other targets."
                )
            );

        } finally {

            setLoadingTargets(false);

        }
    }

    // --------------------------------------------------
    // SIMILARITY CUTOFF
    //
    // Uses the cutoff chosen on the Homologous Proteins
    // slider when there is one, otherwise the server's
    // configured benchmark.
    // --------------------------------------------------

    const activeBenchmark = homologFilter || benchmark;

    function passesBenchmark(target) {

        if (!target.is_homolog) {
            return false;
        }

        if (!homologFilter) {
            return Boolean(target.meets_benchmark);
        }

        const value = target[homologFilter.basis];

        return value != null && value >= homologFilter.threshold;
    }

    const activeBenchmarkCount =
        homologFilter
            ? otherTargets.filter(passesBenchmark).length
            : benchmarkCount;


    // --------------------------------------------------
    // SEARCH TARGETS
    // --------------------------------------------------

    const filteredTargets =
        otherTargets.filter(target => {

            const search =
                targetSearch
                    .toLowerCase()
                    .trim();

            if (!search) {
                return true;
            }

            return (

                String(
                    target.target_name || ""
                )
                    .toLowerCase()
                    .includes(search)

                ||

                String(
                    target.target_chembl_id || ""
                )
                    .toLowerCase()
                    .includes(search)

                ||

                String(
                    target.uniprot_id || ""
                )
                    .toLowerCase()
                    .includes(search)

            );

        });

    const visibleTargets =
        showAllTargets
            ? filteredTargets
            : filteredTargets.slice(0, 10);


    return (

        <div
            style={{
                background: "#1e293b",
                borderRadius: 12,
                padding: 20,
                color: "white"
            }}
        >

            {/* ========================================= */}
            {/* SCAFFOLD IMAGE */}
            {/* ========================================= */}

            <div
                dangerouslySetInnerHTML={{
                    __html: scaffold.svg
                }}
            />

            <hr />

            <h2>
                Rank #{scaffold.rank}
            </h2>

            <p>
                <b>Overall Score :</b>{" "}
                {ranking.overall_score}
            </p>

            <p>
                <b>Grade :</b>{" "}
                {ranking.grade}
            </p>

            <p>
                <b>Status :</b>{" "}
                {ranking.label}
            </p>

            <hr />

            <p>
                <b>Scaffold ID :</b>{" "}
                SCF-{scaffold.id}
            </p>

            <p>
                <b>SMILES :</b>{" "}
                <span
                    style={{
                        wordBreak: "break-all"
                    }}
                >
                    {scaffold.scaffold_smiles}
                </span>
            </p>

            <hr />

            <h3>
                Occurrence
            </h3>

            <p>
                <b>Occurrences :</b>{" "}
                {scaffold.occurrences}
            </p>

            <p>
                <b>Percentage :</b>{" "}
                {scaffold.percentage}%
            </p>

            <p>
                <b>Unique Molecules :</b>{" "}
                {scaffold.unique_molecules}
            </p>

            <p>
                <b>Activity Records :</b>{" "}
                {scaffold.activity_records}
            </p>

            <hr />

            <h3>
                Potency
            </h3>

            <p>
                <b>Maximum pIC50 :</b>{" "}
                {scaffold.max_pic50}
            </p>

            <p>
                <b>Mean pIC50 :</b>{" "}
                {scaffold.mean_pic50}
            </p>

            <p>
                <b>Median pIC50 :</b>{" "}
                {scaffold.median_pic50}
            </p>

            <p>
                <b>Minimum pIC50 :</b>{" "}
                {scaffold.min_pic50}
            </p>

            <p>
                <b>Std Dev :</b>{" "}
                {scaffold.std_pic50}
            </p>

            <hr />

            <h3>
                Drug-Likeness
            </h3>

            <p>
                <b>Drug Score :</b>{" "}
                {drug.druglikeness_score}
            </p>

            <p>
                <b>QED :</b>{" "}
                {descriptors.qed}
            </p>

            <p>
                <b>Lipinski :</b>{" "}
                {drug.lipinski_pass
                    ? "PASS"
                    : "FAIL"}
            </p>

            <p>
                <b>Veber :</b>{" "}
                {drug.veber_pass
                    ? "PASS"
                    : "FAIL"}
            </p>

            <hr />

            <h3>
                Physicochemical Properties
            </h3>

            <p>
                <b>Molecular Weight :</b>{" "}
                {descriptors.molecular_weight}
            </p>

            <p>
                <b>LogP :</b>{" "}
                {descriptors.logp}
            </p>

            <p>
                <b>TPSA :</b>{" "}
                {descriptors.tpsa}
            </p>

            <p>
                <b>HBA :</b>{" "}
                {descriptors.hba}
            </p>

            <p>
                <b>HBD :</b>{" "}
                {descriptors.hbd}
            </p>

            <p>
                <b>Rotatable Bonds :</b>{" "}
                {descriptors.rotatable_bonds}
            </p>

            <p>
                <b>Fraction Csp3 :</b>{" "}
                {descriptors.fsp3}
            </p>

            <hr />

            <h3>
                Complexity
            </h3>

            <p>
                <b>Bertz Complexity :</b>{" "}
                {descriptors.bertz_complexity}
            </p>

            <p>
                <b>Ring Count :</b>{" "}
                {descriptors.ring_count}
            </p>

            <p>
                <b>Aromatic Rings :</b>{" "}
                {descriptors.aromatic_rings}
            </p>


            {/* ========================================= */}
            {/* EXISTING INVESTIGATE BUTTON */}
            {/* ========================================= */}

            <button
                style={{
                    marginTop: 20,
                    width: "100%",
                    padding: 12,
                    cursor: "pointer",
                    borderRadius: 8
                }}
                onClick={() =>
                    onInvestigate(scaffold)
                }
            >
                Investigate Scaffold
            </button>


            {/* ========================================= */}
            {/* FIND OTHER TARGETS */}
            {/* ========================================= */}

            <button
                style={{
                    marginTop: 10,
                    width: "100%",
                    padding: 12,
                    cursor: loadingTargets
                        ? "wait"
                        : "pointer",
                    borderRadius: 8
                }}
                onClick={
                    findOtherTargets
                }
                disabled={
                    loadingTargets
                }
            >

                {loadingTargets
                    ? "Finding Other Targets..."
                    : "Find Other Targets"}

            </button>


            {/* ========================================= */}
            {/* ERROR */}
            {/* ========================================= */}

            {targetError && (

                <p
                    style={{
                        marginTop: 15
                    }}
                >
                    {targetError}
                </p>

            )}


            {/* ========================================= */}
            {/* OTHER TARGETS */}
            {/* ========================================= */}

            {showTargets && (

                <div
                    style={{
                        marginTop: 20
                    }}
                >

                    <hr />

                    <h3>
                        Other Targets
                    </h3>

                    <p>
                        <b>
                            {otherTargets.length}
                        </b>{" "}
                        other target
                        {otherTargets.length !== 1
                            ? "s"
                            : ""}{" "}
                        contain this scaffold.
                    </p>


                    {/* ================================= */}
                    {/* SELECTIVITY READ-OUT              */}
                    {/* ================================= */}

                    {queryUniprot && otherTargets.length > 0 && (

                        <p className="selectivity-note">
                            {homologCount > 0 ? (
                                <>
                                    <b>{homologCount}</b> of them{" "}
                                    {homologCount === 1
                                        ? "is a sequence homolog"
                                        : "are sequence homologs"}{" "}
                                    of your target, so activity here may
                                    be family-wide rather than selective.
                                    {activeBenchmark && (
                                        <>
                                            {" "}
                                            <b>
                                                {activeBenchmarkCount}
                                            </b>{" "}
                                            {activeBenchmarkCount === 1
                                                ? "reaches"
                                                : "reach"}{" "}
                                            {activeBenchmark.threshold}%{" "}
                                            {activeBenchmark.basis}{" "}
                                            or above (marked ✓).
                                        </>
                                    )}
                                </>
                            ) : (
                                <>
                                    None of them is a sequence homolog of
                                    your target, so this overlap is not
                                    driven by protein family similarity.
                                </>
                            )}
                        </p>

                    )}


                    {/* ================================= */}
                    {/* SEARCH */}
                    {/* ================================= */}

                    {otherTargets.length > 10 && (

                        <input
                            type="text"
                            placeholder="Search target..."
                            value={
                                targetSearch
                            }
                            onChange={
                                event =>
                                    setTargetSearch(
                                        event.target.value
                                    )
                            }
                            style={{
                                width: "100%",
                                boxSizing:
                                    "border-box",
                                padding: 10,
                                marginTop: 10,
                                marginBottom: 15,
                                borderRadius: 6,
                                border: "none"
                            }}
                        />

                    )}


                    {/* ================================= */}
                    {/* TARGET LIST */}
                    {/* ================================= */}

                    {visibleTargets.map(
                        target => (

                            <div
                                key={
                                    target.target_chembl_id
                                }
                                style={{
                                    background:
                                        "#0f172a",
                                    padding: 12,
                                    borderRadius: 8,
                                    marginBottom: 10
                                }}
                            >

                                <p
                                    style={{
                                        margin:
                                            "0 0 6px 0"
                                    }}
                                >
                                    <b>
                                        {target.target_name
                                            || "Unknown Target"}
                                    </b>

                                    {target.is_homolog && (

                                        <span
                                            className={
                                                "homolog-badge"
                                                + (passesBenchmark(target)
                                                    ? " benchmark-badge"
                                                    : "")
                                            }
                                            title={
                                                "Sequence identity "
                                                + target.identity
                                                + "%, similarity "
                                                + target.similarity
                                                + "% to the analysed"
                                                + " protein (E-value "
                                                + formatEvalue(
                                                    target.evalue
                                                )
                                                + ")"
                                            }
                                        >
                                            {passesBenchmark(target)
                                                ? "✓ "
                                                : ""}
                                            homolog ·{" "}
                                            {target.identity}% id /{" "}
                                            {target.similarity}% sim
                                        </span>

                                    )}
                                </p>

                                <p
                                    style={{
                                        margin:
                                            "4px 0"
                                    }}
                                >
                                    <b>
                                        ChEMBL:
                                    </b>{" "}
                                    {
                                        target.target_chembl_id
                                    }
                                </p>

                                <p
                                    style={{
                                        margin:
                                            "4px 0"
                                    }}
                                >
                                    <b>
                                        Molecules:
                                    </b>{" "}
                                    {
                                        target.molecule_count
                                    }
                                </p>

                                {target.uniprot_id && (

                                    <p
                                        style={{
                                            margin:
                                                "4px 0"
                                        }}
                                    >
                                        <b>
                                            UniProt:
                                        </b>{" "}
                                        {
                                            target.uniprot_id
                                        }
                                    </p>

                                )}

                            </div>

                        )
                    )}


                    {/* ================================= */}
                    {/* SHOW ALL / SHOW TOP 10 */}
                    {/* ================================= */}

                    {filteredTargets.length > 10 && (

                        <button
                            style={{
                                width: "100%",
                                padding: 10,
                                cursor: "pointer",
                                borderRadius: 8,
                                marginTop: 5
                            }}
                            onClick={() =>
                                setShowAllTargets(
                                    !showAllTargets
                                )
                            }
                        >

                            {showAllTargets
                                ? "Show Top 10"
                                : `Show All ${filteredTargets.length}`}

                        </button>

                    )}

                </div>

            )}

        </div>

    );
}