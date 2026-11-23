import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";

import Navbar from "../components/Navbar";
import Footer from "../components/Footer";
import api, { runAnalysis } from "../services/api";

import "../App.css";
import "../site.css";


const EXAMPLES = [
    { id: "P00533", name: "EGFR" },
    { id: "O60674", name: "JAK2" },
    { id: "P35968", name: "VEGFR2" },
    { id: "Q06187", name: "BTK" },
    { id: "P56817", name: "BACE1" },
    { id: "O60885", name: "BRD4" }
];

const STATS = [
    ["3,030", "protein targets"],
    ["645,282", "unique molecules"],
    ["1,249,719", "activity records"],
    ["6", "linked analyses"]
];

const FEATURES = [
    {
        title: "Scaffold ranking",
        text: "Molecules grouped by Bemis-Murcko scaffold and ranked by population and potency.",
        tag: "Live"
    },
    {
        title: "One-atom differences",
        text: "Pairs of molecules that differ by a single atom, with the change in potency for each.",
        tag: "Live"
    },
    {
        title: "Cross-target scaffolds",
        text: "The same scaffold searched across every other target in the database.",
        tag: "Live"
    },
    {
        title: "Homologous proteins",
        text: "Sequence-similar targets, with a 70% identity benchmark and selectivity by scaffold.",
        tag: "Precomputed"
    },
    {
        title: "Chemical series",
        text: "Fingerprint clustering plus a maximum common substructure for every series.",
        tag: "Precomputed"
    },
    {
        title: "Stereochemistry",
        text: "Enantiomers, diastereomers and E/Z isomers, and how much potency they lose.",
        tag: "Precomputed"
    }
];

const STEPS = [
    ["01", "Enter a target", "A UniProt accession, for example P00533."],
    ["02", "Scaffolds are built", "Activity records are read and every molecule is reduced to its scaffold."],
    ["03", "Open the dashboard", "Summary, composition chart and ranked scaffolds appear first."],
    ["04", "Go deeper on demand", "Homologs, series and stereoisomers load only when you ask."]
];


export default function Home() {

    const [searchParams] = useSearchParams();

    // Allows linking straight to a target, e.g. /?uniprot=P04626
    // (used by the "Homologous Proteins" panel).
    const [uniprot, setUniprot] = useState(
        () => searchParams.get("uniprot") || ""
    );
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(null);
    const [error, setError] = useState("");

    const abortRef = useRef(null);

    const navigate = useNavigate();


    // Wake the backend up as soon as the page opens, so it is ready
    // by the time the user submits (free hosting sleeps when idle).
    useEffect(() => {

        api.get("/health").catch(() => {});

        return () => abortRef.current?.abort();

    }, []);


    async function analyzeTarget(idOverride) {

        const id = (idOverride ?? uniprot).trim();

        if (id === "") {
            setError("Please enter a UniProt ID (for example P00533).");
            return;
        }

        const controller = new AbortController();
        abortRef.current = controller;

        setError("");
        setLoading(true);
        setProgress({
            progress: 0,
            stage: "Connecting to analysis server..."
        });

        try {

            const result = await runAnalysis(
                id,
                (update) => setProgress(update),
                controller.signal
            );

            // "all_scaffolds" is not displayed anywhere and can be
            // large; keeping it out of the browser history state avoids
            // size limits (notably in Safari).
            // eslint-disable-next-line no-unused-vars
            const { all_scaffolds, ...dashboardResult } = result;

            navigate("/dashboard", {
                state: {
                    result: dashboardResult
                }
            });

        }
        catch (err) {

            if (err?.name === "AbortError" || err?.name === "CanceledError") {
                return;
            }

            console.error("Analysis error:", err);

            setError(err?.message || "The analysis failed.");

        }
        finally {

            setLoading(false);
            setProgress(null);

        }

    }

    function handleKeyDown(e) {

        if (e.key === "Enter" && !loading) {
            analyzeTarget();
        }

    }

    function pickExample(id) {

        if (loading) {
            return;
        }

        setUniprot(id);
        analyzeTarget(id);
    }

    return (

        <div className="site">

            <Navbar />

            <main>

                {/* ---------- HERO ---------- */}

                <section className="hero">

                    <div className="wrap hero-grid">

                        <div>

                            <p className="eyebrow">
                                Structure-activity analysis on ChEMBL
                            </p>

                            <h1 className="hero-heading">
                                Find which parts of a molecule drive potency.
                            </h1>

                            <p className="hero-lede">
                                Give it a protein target. It groups every
                                reported compound by scaffold, pairs up
                                near-identical molecules, and shows where a
                                small structural change costs or gains orders
                                of magnitude in activity.
                            </p>

                        </div>

                        <div className="panel search-panel">

                            <label className="field-label" htmlFor="uniprot">
                                UniProt accession
                            </label>

                            <div className="search-row">

                                <input
                                    id="uniprot"
                                    className="text-input mono"
                                    type="text"
                                    value={uniprot}
                                    onChange={(e) => {
                                        setUniprot(e.target.value);
                                        setError("");
                                    }}
                                    onKeyDown={handleKeyDown}
                                    placeholder="P00533"
                                    disabled={loading}
                                    autoComplete="off"
                                    spellCheck="false"
                                />

                                <button
                                    className="btn-primary"
                                    onClick={() => analyzeTarget()}
                                    disabled={loading}
                                >
                                    {loading ? "Analyzing…" : "Analyze"}
                                </button>

                            </div>

                            <div className="example-row">
                                <span>Try</span>
                                {EXAMPLES.map(example => (
                                    <button
                                        key={example.id}
                                        className="chip"
                                        onClick={() => pickExample(example.id)}
                                        disabled={loading}
                                        title={example.id}
                                    >
                                        {example.name}
                                    </button>
                                ))}
                            </div>

                            {error && (
                                <div className="analysis-error" role="alert">
                                    <span className="analysis-error-icon">!</span>
                                    <span>{error}</span>
                                </div>
                            )}

                            {loading && progress && (

                                <div className="analysis-progress" aria-live="polite">

                                    <div className="progress-header">

                                        <span className="progress-stage">
                                            {progress.stage}
                                        </span>

                                        {typeof progress.progress === "number" && (
                                            <span className="progress-percent mono">
                                                {Math.round(progress.progress)}%
                                            </span>
                                        )}

                                    </div>

                                    <div
                                        className={
                                            "progress-track" +
                                            (typeof progress.progress === "number"
                                                ? ""
                                                : " indeterminate")
                                        }
                                        role="progressbar"
                                        aria-valuemin={0}
                                        aria-valuemax={100}
                                        aria-valuenow={
                                            typeof progress.progress === "number"
                                                ? Math.round(progress.progress)
                                                : undefined
                                        }
                                    >
                                        <div
                                            className="progress-fill"
                                            style={{
                                                width:
                                                    typeof progress.progress === "number"
                                                        ? `${Math.max(progress.progress, 2)}%`
                                                        : undefined
                                            }}
                                        />
                                    </div>

                                    <div className="progress-meta">

                                        {progress.status === "queued" ? (
                                            <span>
                                                Waiting for another analysis to finish
                                                {progress.queue_position
                                                    ? ` (position ${progress.queue_position})`
                                                    : ""}
                                            </span>
                                        ) : (
                                            <span>
                                                {typeof progress.elapsed_seconds === "number"
                                                    ? `Elapsed ${Math.floor(progress.elapsed_seconds)}s`
                                                    : "Working..."}
                                            </span>
                                        )}

                                    </div>

                                </div>

                            )}

                            <p className="fine-print">
                                The first request after a quiet period can
                                take up to a minute while the server wakes.
                            </p>

                        </div>

                    </div>

                </section>


                {/* ---------- DATASET ---------- */}

                <section className="stat-strip">

                    <div className="wrap stat-strip-grid">

                        {STATS.map(([value, label]) => (
                            <div className="stat-cell" key={label}>
                                <span className="stat-value mono">{value}</span>
                                <span className="stat-label">{label}</span>
                            </div>
                        ))}

                    </div>

                </section>


                {/* ---------- FEATURES ---------- */}

                <section className="section">

                    <div className="wrap">

                        <h2 className="section-title">What the analysis covers</h2>

                        <p className="section-lede">
                            Each result links back to the molecules behind it,
                            so every number can be traced to structures.
                        </p>

                        <div className="feature-grid">

                            {FEATURES.map((feature, index) => (
                                <article className="feature" key={feature.title}>
                                    <div className="feature-head">
                                        <span className="feature-no mono">
                                            {String(index + 1).padStart(2, "0")}
                                        </span>
                                        <span className="feature-tag mono">
                                            {feature.tag}
                                        </span>
                                    </div>
                                    <h3>{feature.title}</h3>
                                    <p>{feature.text}</p>
                                </article>
                            ))}

                        </div>

                    </div>

                </section>


                {/* ---------- HOW IT WORKS ---------- */}

                <section className="section section-alt">

                    <div className="wrap">

                        <h2 className="section-title">How a session goes</h2>

                        <ol className="steps">

                            {STEPS.map(([no, title, text]) => (
                                <li key={no}>
                                    <span className="step-no mono">{no}</span>
                                    <h3>{title}</h3>
                                    <p>{text}</p>
                                </li>
                            ))}

                        </ol>

                        <p className="section-lede">
                            Clustering, maximum common substructure and
                            stereoisomer search are too slow to run while
                            someone waits, so they are computed once for all
                            targets and looked up. See{" "}
                            <Link to="/methods" className="text-link">
                                Methods
                            </Link>{" "}
                            for the algorithms and parameters.
                        </p>

                    </div>

                </section>

            </main>

            <Footer />

        </div>

    );

}
