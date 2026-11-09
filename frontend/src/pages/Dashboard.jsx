import { useCallback, useState } from "react";
import { useLocation, Navigate, useNavigate } from "react-router-dom";

import SummaryCard from "../components/SummaryCard";
import CompositionChart from "../components/CompositionChart";
import ScaffoldCard from "../components/ScaffoldCard";
import HomologPanel from "../components/HomologPanel";


export default function Dashboard() {

    const location = useLocation();

    const navigate = useNavigate();

    const result = location.state?.result;

    // Similarity cutoff chosen on the Homologous Proteins slider,
    // shared with the scaffold cards so both agree on what counts
    // as a homolog. Declared before any early return so the hook
    // order stays stable.

    const [homologFilter, setHomologFilter] = useState(null);

    const handleHomologFilter = useCallback(

        filter => setHomologFilter(

            previous => (

                previous
                && previous.basis === filter.basis
                && previous.threshold === filter.threshold

                    ? previous
                    : filter

            )

        ),

        []

    );


    // --------------------------------------------------
    // NO RESULT
    // --------------------------------------------------

    if (!result) {

        return <Navigate to="/" />;

    }


    // --------------------------------------------------
    // RESULT DATA
    // --------------------------------------------------

    const summary = result.summary;

    const scaffolds = result.top_scaffolds;

    const chartData = result.charts.composition;


    // --------------------------------------------------
    // INVESTIGATE SCAFFOLD
    // --------------------------------------------------

    function investigate(scaffold) {

        navigate("/scaffold", {

            state: {

                scaffold

            }

        });

    }


    // --------------------------------------------------
    // DASHBOARD
    // --------------------------------------------------

    return (

        <div

            style={{

                padding: 40,

                background: "#0f172a",

                color: "white",

                minHeight: "100vh"

            }}

        >

            {/* ========================================= */}
            {/* TITLE */}
            {/* ========================================= */}

            <h1>

                Scaffold Analyzer

            </h1>


            <br />


            {/* ========================================= */}
            {/* SUMMARY */}
            {/* ========================================= */}

            <div

                style={{

                    display: "grid",

                    gridTemplateColumns:
                        "repeat(4, 1fr)",

                    gap: 20

                }}

            >

                <SummaryCard
                    title="Protein"
                    value={summary.protein}
                />

                <SummaryCard
                    title="Gene"
                    value={summary.gene}
                />

                <SummaryCard
                    title="Target"
                    value={summary.chembl_target}
                />

                <SummaryCard
                    title="Activity Records"
                    value={summary.activity_records}
                />

                <SummaryCard
                    title="Unique Molecules"
                    value={summary.unique_molecules}
                />

                <SummaryCard
                    title="Unique Scaffolds"
                    value={summary.unique_scaffolds}
                />

                <SummaryCard
                    title="Largest Scaffold %"
                    value={
                        summary.largest_scaffold_percentage
                        + "%"
                    }
                />

                <SummaryCard
                    title="Average pIC50"
                    value={summary.average_pic50}
                />

            </div>


            <br />

            <br />


            {/* ========================================= */}
            {/* COMPOSITION CHART */}
            {/* ========================================= */}

            <h2>

                Top 10 Scaffold Composition

            </h2>


            <CompositionChart

                data={chartData}

            />


            <br />

            <br />


            {/* ========================================= */}
            {/* HOMOLOGOUS PROTEINS */}
            {/* ========================================= */}

            <HomologPanel

                homologs={result.homologs}

                onFilterChange={handleHomologFilter}

            />


            <br />


            {/* ========================================= */}
            {/* TOP SCAFFOLDS */}
            {/* ========================================= */}

            <h2>

                Top Ranked Scaffolds

            </h2>


            <div

                style={{

                    display: "grid",

                    gridTemplateColumns:
                        "repeat(auto-fill,minmax(460px,1fr))",

                    gap: 20

                }}

            >

                {

                    scaffolds.map(

                        scaffold => (

                            <ScaffoldCard

                                key={scaffold.id}

                                scaffold={scaffold}

                                onInvestigate={
                                    investigate
                                }

                                /*
                                 * IMPORTANT:
                                 *
                                 * Pass the currently
                                 * analyzed target to
                                 * ScaffoldCard.
                                 *
                                 * Feature A uses this
                                 * to exclude the current
                                 * target and show only
                                 * OTHER targets.
                                 */

                                currentTarget={
                                    summary.chembl_target
                                }

                                /*
                                 * UniProt ID of the analysed
                                 * protein, so cross-target hits
                                 * can be marked as sequence
                                 * homologs of it.
                                 */

                                queryUniprot={
                                    summary.uniprot
                                }

                                /*
                                 * Keeps the scaffold cards on the same
                                 * similarity cutoff as the slider in
                                 * the Homologous Proteins panel.
                                 */

                                homologFilter={homologFilter}

                            />

                        )

                    )

                }

            </div>

        </div>

    );

}