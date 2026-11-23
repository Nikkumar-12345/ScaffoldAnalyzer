import { useCallback, useState } from "react";
import { useLocation, Navigate, useNavigate, Link } from "react-router-dom";

import SummaryCard from "../components/SummaryCard";
import CompositionChart from "../components/CompositionChart";
import ScaffoldCard from "../components/ScaffoldCard";
import HomologPanel from "../components/HomologPanel";
import MCSPanel from "../components/MCSPanel";
import StereoPanel from "../components/StereoPanel";
import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

import "../App.css";
import "../site.css";


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

    const fmt = value => (
        typeof value === "number" ? value.toLocaleString("en-US") : value
    );

    const kpis = [
        ["Activity records", fmt(summary.activity_records), true],
        ["Unique molecules", fmt(summary.unique_molecules), true],
        ["Unique scaffolds", fmt(summary.unique_scaffolds), true],
        ["Mean pIC50", summary.average_pic50, true],
        ["Top scaffold share", summary.largest_scaffold_percentage + "%", true],
        ["ChEMBL target", summary.chembl_target, true],
        ["Gene", summary.gene, false],
        ["UniProt", summary.uniprot, true]
    ];

    const shownKpis = kpis.filter(([, value]) => value !== null && value !== undefined && value !== "");

    return (

        <div className="site">

            <Navbar />

            <main className="wrap">

                <div className="dash-head">

                    <Link to="/" className="dash-back">
                        ← Analyze another target
                    </Link>

                    <h1>{summary.protein}</h1>

                    <div className="dash-meta">
                        {summary.gene && (
                            <span>Gene <strong>{summary.gene}</strong></span>
                        )}
                        <span>UniProt <strong className="mono">{summary.uniprot}</strong></span>
                        <span>ChEMBL <strong className="mono">{summary.chembl_target}</strong></span>
                    </div>

                </div>

                <div className="kpi-grid">

                    {shownKpis.map(([label, value, mono]) => (
                        <div className="kpi" key={label}>
                            <span className="kpi-label">{label}</span>
                            <span className={"kpi-value" + (mono ? " mono" : "")}>
                                {value ?? "-"}
                            </span>
                        </div>
                    ))}

                </div>

                <section className="dash-section">

                    <h2>Top 10 scaffold composition</h2>

                    <p className="dash-sub">
                        Share of the target's molecules carried by each of
                        the ten most populated scaffolds.
                    </p>

                    <CompositionChart data={chartData} />

                </section>

                <section className="dash-section">

                    <HomologPanel
                        homologs={result.homologs}
                        onFilterChange={handleHomologFilter}
                    />

                </section>

                {summary.uniprot && (

                    <>
                        <section className="dash-section">
                            <MCSPanel uniprot={summary.uniprot} />
                        </section>

                        <section className="dash-section">
                            <StereoPanel uniprot={summary.uniprot} />
                        </section>
                    </>

                )}

                <section className="dash-section">

                    <h2>Top ranked scaffolds</h2>

                    <p className="dash-sub">
                        Open a scaffold to compare its molecules, side
                        chains and cross-target activity.
                    </p>

                    <div className="scaffold-grid">

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

                </section>

            </main>

            <Footer />

        </div>

    );

}