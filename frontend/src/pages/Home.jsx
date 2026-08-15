import { useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import api from "../services/api";

import "../App.css";

export default function Home() {
    const [uniprot, setUniprot] = useState("");
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    async function analyzeTarget() {
        if (uniprot.trim() === "") {
            alert("Please enter a UniProt ID");
            return;
        }

        try {
            setLoading(true);

            const response = await api.post("/analyze/", {
                uniprot_id: uniprot.trim()
            });

            console.log("SUCCESS");
            console.log(response.data);

            navigate("/dashboard", {
                state: {
                    result: response.data
                }
            });
        }
        catch (err) {
            console.log("===== ERROR =====");
            console.log(err);

            if (err.response) {
                console.log("Status:", err.response.status);
                console.log("Data:", err.response.data);

                alert(
                    "Backend Error\n\n" +
                    JSON.stringify(err.response.data, null, 2)
                );
            }
            else if (err.request) {
                console.log(err.request);

                alert(
                    "Cannot connect to backend.\n\n" +
                    "Make sure FastAPI is running on port 8000."
                );
            }
            else {
                console.log(err.message);
                alert(err.message);
            }
        }
        finally {
            setLoading(false);
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
                                    onChange={(e) =>
                                        setUniprot(e.target.value)
                                    }
                                    onKeyDown={handleKeyDown}
                                    placeholder="Example: P00533"
                                    disabled={loading}
                                />
                            </div>

                            <p className="example-text">
                                Try: <strong>P00533</strong> (EGFR)
                            </p>

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