import { Link } from "react-router-dom";

import Navbar from "../components/Navbar";
import Footer from "../components/Footer";

import "../App.css";
import "../site.css";


const METHODS = [
    {
        id: "scaffolds",
        title: "Scaffold ranking",
        mode: "Computed per request",
        steps: [
            "Every molecule with a measured activity against the target is parsed with RDKit.",
            "Its Bemis-Murcko scaffold is extracted: ring systems and the linkers between them, with side chains removed.",
            "Molecules sharing a canonical scaffold SMILES form one group. Groups are ranked by size and potency."
        ],
        note: "Molecules with no ring system have no scaffold and are counted separately."
    },
    {
        id: "one-atom",
        title: "One-atom differences and activity cliffs",
        mode: "Computed per request",
        steps: [
            "Within a scaffold, two molecules are compared by their element counts.",
            "A pair qualifies when the second has exactly one atom added, removed, or swapped for a different element.",
            "The change in potency is ΔpIC50. At 1.0 or more (10-fold) the pair is flagged a moderate potential cliff; at 2.0 or more (100-fold), a strong one."
        ],
        note: "A flagged pair is a lead for inspection, not proof of a cliff: assay differences between papers can produce the same gap."
    },
    {
        id: "cross-target",
        title: "Cross-target scaffolds",
        mode: "Computed per request",
        steps: [
            "A scaffold is looked up against every other target in the indexed database.",
            "Targets that share it are listed with their molecule counts and potency."
        ],
        note: "Targets that are sequence homologs of the query are marked, so shared chemistry that is expected can be told apart from the unexpected."
    },
    {
        id: "homologs",
        title: "Homologous proteins",
        mode: "Precomputed",
        steps: [
            "Every target was aligned against every other with a Smith-Waterman local alignment, BLOSUM62, and the standard BLAST gap penalties.",
            "Percent identity, coverage and bit score are stored for the most significant hits.",
            "The slider and the 70% benchmark are applied to the stored values, so changing them is instant."
        ],
        note: "Below roughly 25% identity, sequence alone says little about shared function. Bands in the interface follow that convention."
    },
    {
        id: "series",
        title: "Chemical series and maximum common substructure",
        mode: "Precomputed",
        steps: [
            "Each molecule is encoded as a Morgan fingerprint (radius 2, the ECFP4 convention).",
            "Molecules are clustered with the Taylor-Butina algorithm at a Tanimoto similarity of 0.6 or more.",
            "For each cluster, RDKit searches for the maximum common substructure, requiring whole rings and ring-to-ring matches."
        ],
        note: "Finding a maximum common substructure is NP-hard, so each search has a time limit. Series that hit it are shown as timed out rather than given a partial answer."
    },
    {
        id: "stereo",
        title: "Stereochemistry",
        mode: "Precomputed",
        steps: [
            "Each molecule is reduced to a flat key with all stereo information removed. Molecules sharing a flat key but differing in 3D arrangement form a group.",
            "Stereocentres and double bonds are found with RDKit, and each pair is classed as enantiomers (mirror images), diastereomers, E/Z isomers, or specified versus unspecified.",
            "Potency per molecule is the mean pChEMBL value over exact measurements. The spread inside a group is its ΔpIC50, with the same 1.0 and 2.0 cliff thresholds."
        ],
        note: "Scaffold grouping cannot separate stereoisomers because they share every atom and bond. A group where one mirror image is far weaker is direct evidence of a stereospecific interaction."
    }
];


export default function Methods() {

    return (

        <div className="site">

            <Navbar />

            <main className="wrap page">

                <p className="eyebrow">Methods</p>

                <h1 className="page-title">
                    How each number is produced
                </h1>

                <p className="page-lede">
                    Six analyses, one data source. Three run when you press
                    Analyze. The other three are computed once for every
                    target and looked up, because they are too slow to run
                    while someone waits.
                </p>

                <div className="panel conventions">

                    <h2>Conventions used throughout</h2>

                    <dl>
                        <div>
                            <dt>Potency</dt>
                            <dd>
                                pIC50, taken from the ChEMBL pChEMBL value.
                                Higher means more potent; one unit is a
                                ten-fold change.
                            </dd>
                        </div>
                        <div>
                            <dt>Measurements used</dt>
                            <dd>
                                Exact values only (relation “=”).
                                Censored results such as “&gt; 10 µM” are
                                left out.
                            </dd>
                        </div>
                        <div>
                            <dt>Structures</dt>
                            <dd>
                                Parsed and canonicalised with RDKit. For
                                salts and mixtures the largest fragment is
                                kept.
                            </dd>
                        </div>
                    </dl>

                </div>

                {METHODS.map((method, index) => (

                    <section className="method" id={method.id} key={method.id}>

                        <div className="method-side">
                            <span className="method-no mono">
                                {String(index + 1).padStart(2, "0")}
                            </span>
                            <span className="feature-tag mono">
                                {method.mode}
                            </span>
                        </div>

                        <div className="method-body">

                            <h2>{method.title}</h2>

                            <ol className="method-steps">
                                {method.steps.map(step => (
                                    <li key={step}>{step}</li>
                                ))}
                            </ol>

                            <p className="method-note">{method.note}</p>

                        </div>

                    </section>

                ))}

                <p className="page-lede">
                    Ready to try it?{" "}
                    <Link to="/" className="text-link">
                        Analyze a target
                    </Link>
                    .
                </p>

            </main>

            <Footer />

        </div>

    );

}
