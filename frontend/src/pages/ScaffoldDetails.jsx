import { useEffect, useState } from "react";
import { useLocation, Navigate } from "react-router-dom";

import api from "../services/api";
import MoleculeCard from "../components/MoleculeCard";

export default function ScaffoldDetails() {

    const location = useLocation();

    const scaffold = location.state?.scaffold;

    const [molecules, setMolecules] = useState([]);

    const [loading, setLoading] = useState(true);


    useEffect(() => {

        if (!scaffold) return;

        api.post(
            "/scaffold/details",
            {
                molecules: scaffold.molecules
            }
        )
        .then((res) => {

            setMolecules(
                res.data.molecules || []
            );

            setLoading(false);

        })
        .catch((err) => {

            console.log(err);

            setLoading(false);

        });

    }, [scaffold]);


    if (!scaffold) {

        return <Navigate to="/dashboard" />;

    }


    const descriptors =
        scaffold.descriptors || {};

    const drug =
        scaffold.druglikeness || {};

    const ranking =
        scaffold.ranking || {};


    // ------------------------------------
    // ONE-ATOM ANALYSIS
    // ------------------------------------

    const oneAtomAnalysis =
        scaffold.side_chain_analysis || {};

    const pairs =
        oneAtomAnalysis.one_atom_pairs || [];


    return (

        <div
            style={{
                background: "#0f172a",
                color: "white",
                minHeight: "100vh",
                padding: "40px"
            }}
        >

            {/* -------------------------------- */}
            {/* PAGE TITLE */}
            {/* -------------------------------- */}

            <h1>
                Scaffold Details
            </h1>

            <br />


            {/* -------------------------------- */}
            {/* SCAFFOLD INFORMATION */}
            {/* -------------------------------- */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "350px 1fr",
                    gap: "40px"
                }}
            >

                <div
                    style={{
                        background: "#1e293b",
                        padding: 20,
                        borderRadius: 12
                    }}
                >

                    <div
                        dangerouslySetInnerHTML={{
                            __html: scaffold.svg
                        }}
                    />

                </div>


                <div>

                    <h2>
                        Scaffold Information
                    </h2>


                    <p>
                        <b>Rank :</b>{" "}
                        {scaffold.rank}
                    </p>


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


                    <p>
                        <b>Drug Score :</b>{" "}
                        {drug.druglikeness_score}
                    </p>


                    <p>
                        <b>QED :</b>{" "}
                        {descriptors.qed}
                    </p>

                </div>

            </div>


            <br />
            <hr />
            <br />


            {/* -------------------------------- */}
            {/* ONE ATOM DIFFERENCE ANALYSIS */}
            {/* -------------------------------- */}

            <h2>
                One-Atom Difference Analysis
            </h2>


            <p
                style={{
                    color: "#cbd5e1"
                }}
            >
                {
                    oneAtomAnalysis.message
                    ||
                    "No one-atom analysis available."
                }
            </p>


            <br />


            {/* SUMMARY BOXES */}

            <div
                style={{
                    display: "flex",
                    gap: 20,
                    flexWrap: "wrap",
                    marginBottom: 25
                }}
            >

                <div
                    style={{
                        background: "#1e293b",
                        padding: 15,
                        borderRadius: 10
                    }}
                >

                    <b>Total Pairs Checked:</b>
                    {" "}
                    {
                        oneAtomAnalysis.total_pairs_checked
                        || 0
                    }

                </div>


                <div
                    style={{
                        background: "#1e293b",
                        padding: 15,
                        borderRadius: 10
                    }}
                >

                    <b>Valid One-Atom Pairs:</b>
                    {" "}
                    {
                        oneAtomAnalysis.valid_one_atom_pairs
                        || 0
                    }

                </div>


                <div
                    style={{
                        background: "#7f1d1d",
                        padding: 15,
                        borderRadius: 10
                    }}
                >

                    <b>Strong Potential Cliffs:</b>
                    {" "}
                    {
                        oneAtomAnalysis.strong_cliffs
                        || 0
                    }

                </div>


                <div
                    style={{
                        background: "#78350f",
                        padding: 15,
                        borderRadius: 10
                    }}
                >

                    <b>Moderate Potential Cliffs:</b>
                    {" "}
                    {
                        oneAtomAnalysis.moderate_cliffs
                        || 0
                    }

                </div>

            </div>


            {/* -------------------------------- */}
            {/* PAIRS TABLE */}
            {/* -------------------------------- */}

            {

                pairs.length === 0

                ?

                (

                    <div
                        style={{
                            background: "#1e293b",
                            padding: 20,
                            borderRadius: 12
                        }}
                    >

                        No molecule pairs with a single
                        atom-level difference were found
                        for this scaffold.

                    </div>

                )

                :

                (

                    <div
                        style={{
                            overflowX: "auto",
                            borderRadius: 12
                        }}
                    >

                        <table
                            style={{
                                width: "100%",
                                borderCollapse: "collapse",
                                background: "#1e293b",
                                color: "white"
                            }}
                        >

                            <thead>

                                <tr
                                    style={{
                                        background: "#334155"
                                    }}
                                >

                                    <th style={{ padding: 12 }}>
                                        Molecule 1
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        Substituent 1
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        pIC50 1
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        Molecule 2
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        Substituent 2
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        pIC50 2
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        Structural Change
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        ΔpIC50
                                    </th>

                                    <th style={{ padding: 12 }}>
                                        Cliff Result
                                    </th>

                                </tr>

                            </thead>


                            <tbody>

                                {

                                    pairs.map(

                                        (pair, index) => (

                                            <tr
                                                key={index}

                                                style={{

                                                    borderBottom:
                                                        "1px solid #475569",


                                                    background:

                                                        pair.delta_pic50 >= 2

                                                        ?

                                                        "#7f1d1d"

                                                        :

                                                        pair.delta_pic50 >= 1

                                                        ?

                                                        "#78350f"

                                                        :

                                                        "#1e293b"

                                                }}
                                            >

                                                <td
                                                    style={{
                                                        padding: 12
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_1
                                                        ?.chembl_id
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12,
                                                        maxWidth: 180,
                                                        wordBreak:
                                                            "break-all"
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_1
                                                        ?.substituent
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_1
                                                        ?.pic50
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_2
                                                        ?.chembl_id
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12,
                                                        maxWidth: 180,
                                                        wordBreak:
                                                            "break-all"
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_2
                                                        ?.substituent
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12
                                                    }}
                                                >

                                                    {
                                                        pair.molecule_2
                                                        ?.pic50
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12,
                                                        fontWeight: "bold"
                                                    }}
                                                >

                                                    {
                                                        pair.structural_change
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12,
                                                        fontWeight: "bold",
                                                        fontSize: 18
                                                    }}
                                                >

                                                    {
                                                        pair.delta_pic50
                                                    }

                                                </td>


                                                <td
                                                    style={{
                                                        padding: 12,
                                                        fontWeight: "bold"
                                                    }}
                                                >

                                                    {
                                                        pair.cliff_type
                                                    }

                                                </td>

                                            </tr>

                                        )

                                    )

                                }

                            </tbody>

                        </table>

                    </div>

                )

            }


            <br />
            <hr />
            <br />


            {/* -------------------------------- */}
            {/* MOLECULES */}
            {/* -------------------------------- */}

            <h2>
                Molecules
            </h2>


            <p>

                Total Molecules:

                {" "}

                {scaffold.unique_molecules}

            </p>


            <br />


            {

                loading &&

                <h2>
                    Loading Molecules...
                </h2>

            }


            {

                !loading
                &&
                molecules.length === 0
                &&

                <p>
                    No molecule details available.
                </p>

            }


            <div
                style={{
                    display: "grid",
                    gridTemplateColumns:
                        "repeat(auto-fill,minmax(340px,1fr))",
                    gap: 20
                }}
            >

                {

                    molecules.map(

                        (molecule, index) => (

                            <MoleculeCard

                                key={index}

                                molecule={molecule}

                            />

                        )

                    )

                }

            </div>


        </div>

    );

}