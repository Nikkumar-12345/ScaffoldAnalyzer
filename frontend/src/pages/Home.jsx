import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import api, { runAnalysis } from "../services/api";

import "../App.css";

export default function Home() {

    const [uniprot, setUniprot] = useState("");
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


    async function analyzeTarget() {

        const id = uniprot.trim();

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

    return (

        <div className="home-page">

            <Navbar />

            <main className="home-main">

                <div className="background-orb orb-one"></div>
                <div className="background-orb orb-two"></div>
                <div className="background-grid"></div>

                <section className="hero-section">

                    <div className="hero-content">

                        <div className="hero-badge">
                            <span className="badge-dot"></span>
                            Molecular Intelligence Platform
                        </div>

                        <h1 className="hero-title">
                            Explore Molecular
                            <span> Scaffolds</span>
                        </h1>

                        <p className="hero-description">
                            Analyze bioactive compounds, identify molecular
                            scaffolds, explore structural patterns, and detect
                            potential activity cliffs from ChEMBL data.
                        </p>

                        <div className="hero-features">

                            <div className="feature-item">
                                <span className="feature-icon">⌬</span>
                                Scaffold Analysis
                            </div>

                            <div className="feature-item">
                                <span className="feature-icon">◈</span>
                                Side Chain Comparison
                            </div>

                            <div className="feature-item">
                                <span className="feature-icon">↗</span>
                                Activity Cliff Detection
                            </div>

                        </div>

                    </div>


                    <div className="analysis-card">

                        <div className="card-glow"></div>

                        <div className="analysis-card-content">

                            <div className="card-top">

                                <div>

                                    <p className="card-label">
                                        START ANALYSIS
                                    </p>

                                    <h2>
                                        Analyze a Target
                                    </h2>

                                </div>

                                <div className="molecule-logo">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>

                            </div>

                            <p className="input-description">
                                Enter a UniProt ID to retrieve target activity
                                data and begin scaffold analysis.
                            </p>

                            <label className="input-label">
                                UniProt ID
                            </label>

                            <div className="input-wrapper">

                                <span className="search-icon">⌕</span>

                                <input
                                    type="text"
                                    value={uniprot}
                                    onChange={(e) => {
                                        setUniprot(e.target.value);
                                        setError("");
                                    }}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Example: P00533"
                                    disabled={loading}
                                />

                            </div>

                            <p className="example-text">
                                Try: <strong>P00533</strong> (EGFR)
                            </p>

                            {error && (

                                <div
                                    className="analysis-error"
                                    role="alert"
                                >
                                    <span className="analysis-error-icon">!</span>
                                    <span>{error}</span>
                                </div>

                            )}

                            <button
                                className="analyze-button"
                                onClick={analyzeTarget}
                                disabled={loading}
                            >

                                {loading ? (
                                    <>
                                        <span className="button-loader"></span>
                                        Analyzing Target...
                                    </>
                                ) : (
                                    <>
                                        Analyze Target
                                        <span className="button-arrow">→</span>
                                    </>
                                )}

                            </button>

                            {loading && progress && (

                                <div
                                    className="analysis-progress"
                                    aria-live="polite"
                                >

                                    <div className="progress-header">

                                        <span className="progress-stage">
                                            {progress.stage}
                                        </span>

                                        {typeof progress.progress === "number" && (
                                            <span className="progress-percent">
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

                            <div className="card-footer">
                                <span className="footer-status-dot"></span>
                                Powered by molecular activity data
                            </div>

                        </div>

                    </div>

                </section>

            </main>

        </div>

    );

}