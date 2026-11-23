import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

import "../App.css";
import "../site.css";


const STACK = [
    ["Backend", "FastAPI, RDKit, SQLite"],
    ["Frontend", "React, Vite, Recharts"],
    ["Data", "ChEMBL activity records, UniProt sequences"],
    ["Hosting", "Render (API), Vercel (web)"]
];

const LIMITS = [
    "Only targets with measured pChEMBL activity in the local ChEMBL copy are indexed (3,030 of them). Others return a clear not-found message.",
    "Potency from different papers and assay formats is pooled. Large gaps between near-identical molecules can reflect assay differences as well as chemistry.",
    "Stereo-groups only form where the database actually holds several isomers of the same structure. Many molecules were reported as a single isomer or without stereo labels.",
    "Maximum common substructure searches have a time limit; a small share of series are marked timed out.",
    "The server is on a free tier and sleeps when idle, so the first request after a quiet period is slow."
];


export default function About() {

    return (

        <div className="site">

            <Navbar />

            <main className="wrap page">

                <p className="eyebrow">About</p>

                <h1 className="page-title">
                    A tool for reading structure-activity data
                </h1>

                <p className="page-lede">
                    ScaffoldAnalyzer was built to make one question quick to
                    ask of public bioactivity data: for this protein, which
                    structural features go with potency, and where does a
                    small change matter most? It is a research aid for
                    exploring hypotheses, and not a substitute for
                    experimental confirmation.
                </p>

                <section className="about-grid">

                    <div className="panel">
                        <h2>Built with</h2>
                        <dl className="kv">
                            {STACK.map(([key, value]) => (
                                <div key={key}>
                                    <dt>{key}</dt>
                                    <dd>{value}</dd>
                                </div>
                            ))}
                        </dl>
                    </div>

                    <div className="panel">
                        <h2>Source and licence</h2>
                        <p className="plain">
                            Activity data comes from ChEMBL, which is
                            released under CC BY-SA 3.0. The code is
                            open on GitHub.
                        </p>
                        <a
                            className="btn-secondary"
                            href="https://github.com/Nikkumar-12345/ScaffoldAnalyzer"
                            target="_blank"
                            rel="noreferrer"
                        >
                            View the repository ↗
                        </a>
                    </div>

                </section>

                <section className="panel limits">

                    <h2>Things to keep in mind</h2>

                    <ul>
                        {LIMITS.map(item => (
                            <li key={item}>{item}</li>
                        ))}
                    </ul>

                </section>

            </main>

            <Footer />

        </div>

    );

}
