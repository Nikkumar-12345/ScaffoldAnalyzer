import { useEffect, useState } from "react";
import { useLocation, Navigate } from "react-router-dom";

import api from "../services/api";
import MoleculeCard from "../components/MoleculeCard";

export default function ScaffoldDetails() {

    const location = useLocation();

    const scaffold = location.state?.scaffold;

    const [molecules, setMolecules] = useState([]);

    const [loading, setLoading] = useState(true);


    // ==============================================
    // FETCH MOLECULE DETAILS
    // ==============================================

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


    // ==============================================
    // ONE-ATOM ANALYSIS
    // ==============================================

    const oneAtomAnalysis =
        scaffold.side_chain_analysis || {};

    const pairs =
        oneAtomAnalysis.one_atom_pairs || [];


    // ==============================================
    // DOWNLOAD SCAFFOLD IMAGE
    // ==============================================

    function downloadScaffoldImage() {

        if (!scaffold.svg) {

            alert("Scaffold image is not available.");
            return;

        }

        const blob = new Blob(
            [scaffold.svg],
            {
                type: "image/svg+xml"
            }
        );

        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            `scaffold_rank_${scaffold.rank}.svg`;

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);

        URL.revokeObjectURL(url);

    }


    // ==============================================
    // DOWNLOAD ONE-ATOM DATA AS CSV
    // ==============================================

    function downloadOneAtomCSV() {

        if (pairs.length === 0) {

            alert(
                "No one-atom difference pairs are available."
            );

            return;

        }

        const headers = [
            "Molecule 1",
            "Substituent 1",
            "pIC50 1",
            "Molecule 2",
            "Substituent 2",
            "pIC50 2",
            "Structural Change",
            "Delta pIC50",
            "Cliff Result"
        ];


        const rows = pairs.map(
            (pair) => [

                pair.molecule_1?.chembl_id || "",

                pair.molecule_1?.substituent || "",

                pair.molecule_1?.pic50 || "",

                pair.molecule_2?.chembl_id || "",

                pair.molecule_2?.substituent || "",

                pair.molecule_2?.pic50 || "",

                pair.structural_change || "",

                pair.delta_pic50 || "",

                pair.cliff_type || ""

            ]
        );


        const escapeCSV = (value) => {

            const stringValue =
                String(value ?? "");

            return `"${stringValue.replace(/"/g, '""')}"`;

        };


        const csvContent =
            [
                headers.map(escapeCSV).join(","),

                ...rows.map(
                    row =>
                        row
                            .map(escapeCSV)
                            .join(",")
                )
            ].join("\n");


        const blob = new Blob(
            [csvContent],
            {
                type: "text/csv;charset=utf-8;"
            }
        );


        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            `one_atom_analysis_scaffold_rank_${scaffold.rank}.csv`;

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);

        URL.revokeObjectURL(url);

    }


    // ==============================================
    // DOWNLOAD COMPLETE SCAFFOLD REPORT AS HTML
    // ==============================================

    function downloadScaffoldReport() {

        const pairRows =
            pairs.length > 0

                ? pairs.map(
                    (pair) => `

                        <tr>

                            <td>
                                ${pair.molecule_1?.chembl_id || ""}
                            </td>

                            <td>
                                ${pair.molecule_1?.substituent || ""}
                            </td>

                            <td>
                                ${pair.molecule_1?.pic50 || ""}
                            </td>

                            <td>
                                ${pair.molecule_2?.chembl_id || ""}
                            </td>

                            <td>
                                ${pair.molecule_2?.substituent || ""}
                            </td>

                            <td>
                                ${pair.molecule_2?.pic50 || ""}
                            </td>

                            <td>
                                ${pair.structural_change || ""}
                            </td>

                            <td>
                                ${pair.delta_pic50 || ""}
                            </td>

                            <td>
                                ${pair.cliff_type || ""}
                            </td>

                        </tr>

                    `
                ).join("")

                : `

                    <tr>

                        <td colspan="9">

                            No one-atom difference pairs found.

                        </td>

                    </tr>

                `;


        const moleculeRows =
            molecules.length > 0

                ? molecules.map(
                    (molecule) => `

                        <tr>

                            <td>
                                ${molecule.chembl_id || ""}
                            </td>

                            <td>
                                ${molecule.pic50 || ""}
                            </td>

                            <td>
                                ${molecule.smiles || ""}
                            </td>

                        </tr>

                    `
                ).join("")

                : `

                    <tr>

                        <td colspan="3">

                            Molecule details were not available.

                        </td>

                    </tr>

                `;


        const reportHTML = `

<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <title>
        Scaffold Report - Rank ${scaffold.rank}
    </title>

    <style>

        body {

            font-family:
                Arial,
                sans-serif;

            padding: 40px;

            color: #1e293b;

            background: white;

        }

        h1 {

            color: #0f172a;

            border-bottom:
                3px solid #2563eb;

            padding-bottom: 10px;

        }

        h2 {

            margin-top: 35px;

            color: #1d4ed8;

        }

        .summary {

            display: grid;

            grid-template-columns:
                repeat(3, 1fr);

            gap: 15px;

            margin-top: 20px;

        }

        .box {

            padding: 15px;

            border:
                1px solid #cbd5e1;

            border-radius: 8px;

            background: #f8fafc;

        }

        .label {

            font-weight: bold;

            color: #475569;

        }

        .scaffold-image {

            margin-top: 20px;

            padding: 20px;

            border:
                1px solid #cbd5e1;

            border-radius: 10px;

            text-align: center;

        }

        table {

            width: 100%;

            border-collapse: collapse;

            margin-top: 15px;

            font-size: 13px;

        }

        th {

            background: #1e293b;

            color: white;

            padding: 10px;

            text-align: left;

        }

        td {

            border:
                1px solid #cbd5e1;

            padding: 8px;

            word-break: break-word;

        }

        tr:nth-child(even) {

            background: #f8fafc;

        }

        .footer {

            margin-top: 40px;

            padding-top: 15px;

            border-top:
                1px solid #cbd5e1;

            color: #64748b;

            font-size: 12px;

        }

    </style>

</head>

<body>

    <h1>
        Scaffold Analysis Report
    </h1>


    <div class="scaffold-image">

        ${scaffold.svg || ""}

    </div>


    <h2>
        Scaffold Information
    </h2>


    <div class="summary">

        <div class="box">

            <div class="label">
                Rank
            </div>

            ${scaffold.rank || ""}

        </div>


        <div class="box">

            <div class="label">
                Overall Score
            </div>

            ${ranking.overall_score || ""}

        </div>


        <div class="box">

            <div class="label">
                Grade
            </div>

            ${ranking.grade || ""}

        </div>


        <div class="box">

            <div class="label">
                Status
            </div>

            ${ranking.label || ""}

        </div>


        <div class="box">

            <div class="label">
                Drug Score
            </div>

            ${drug.druglikeness_score || ""}

        </div>


        <div class="box">

            <div class="label">
                QED
            </div>

            ${descriptors.qed || ""}

        </div>

    </div>


    <h2>
        One-Atom Difference Analysis
    </h2>


    <div class="summary">

        <div class="box">

            <div class="label">
                Total Pairs Checked
            </div>

            ${oneAtomAnalysis.total_pairs_checked || 0}

        </div>


        <div class="box">

            <div class="label">
                Valid One-Atom Pairs
            </div>

            ${oneAtomAnalysis.valid_one_atom_pairs || 0}

        </div>


        <div class="box">

            <div class="label">
                Strong Potential Cliffs
            </div>

            ${oneAtomAnalysis.strong_cliffs || 0}

        </div>


        <div class="box">

            <div class="label">
                Moderate Potential Cliffs
            </div>

            ${oneAtomAnalysis.moderate_cliffs || 0}

        </div>

    </div>


    <p>

        ${oneAtomAnalysis.message || ""}

    </p>


    <h2>
        One-Atom Difference Pairs
    </h2>


    <table>

        <thead>

            <tr>

                <th>Molecule 1</th>

                <th>Substituent 1</th>

                <th>pIC50 1</th>

                <th>Molecule 2</th>

                <th>Substituent 2</th>

                <th>pIC50 2</th>

                <th>Structural Change</th>

                <th>ΔpIC50</th>

                <th>Cliff Result</th>

            </tr>

        </thead>

        <tbody>

            ${pairRows}

        </tbody>

    </table>


    <h2>
        Molecules
    </h2>


    <table>

        <thead>

            <tr>

                <th>ChEMBL ID</th>

                <th>pIC50</th>

                <th>SMILES</th>

            </tr>

        </thead>

        <tbody>

            ${moleculeRows}

        </tbody>

    </table>


    <div class="footer">

        Generated using Scaffold Analyzer

    </div>


</body>

</html>

        `;


        const blob = new Blob(
            [reportHTML],
            {
                type: "text/html"
            }
        );


        const url =
            URL.createObjectURL(blob);

        const link =
            document.createElement("a");

        link.href = url;

        link.download =
            `scaffold_report_rank_${scaffold.rank}.html`;

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);

        URL.revokeObjectURL(url);

    }


    // ==============================================
    // PAGE
    // ==============================================

    return (

        <div
            style={{
                background: "#0f172a",
                color: "white",
                minHeight: "100vh",
                padding: "40px"
            }}
        >

            <h1>
                Scaffold Details
            </h1>

            <br />


            {/* ========================================= */}
            {/* DOWNLOAD BUTTONS */}
            {/* ========================================= */}

            <div
                style={{
                    display: "flex",
                    gap: 15,
                    flexWrap: "wrap",
                    marginBottom: 30
                }}
            >

                <button
                    onClick={downloadScaffoldImage}
                    style={{
                        padding: "12px 20px",
                        borderRadius: 8,
                        border: "none",
                        cursor: "pointer",
                        fontSize: 15,
                        fontWeight: "bold",
                        background: "#2563eb",
                        color: "white"
                    }}
                >
                    Download Scaffold Image
                </button>


                <button
                    onClick={downloadScaffoldReport}
                    style={{
                        padding: "12px 20px",
                        borderRadius: 8,
                        border: "none",
                        cursor: "pointer",
                        fontSize: 15,
                        fontWeight: "bold",
                        background: "#059669",
                        color: "white"
                    }}
                >
                    Download Scaffold Report
                </button>


                <button
                    onClick={downloadOneAtomCSV}
                    disabled={pairs.length === 0}
                    style={{
                        padding: "12px 20px",
                        borderRadius: 8,
                        border: "none",
                        cursor:
                            pairs.length === 0
                                ? "not-allowed"
                                : "pointer",
                        fontSize: 15,
                        fontWeight: "bold",
                        background:
                            pairs.length === 0
                                ? "#475569"
                                : "#d97706",
                        color: "white",
                        opacity:
                            pairs.length === 0
                                ? 0.6
                                : 1
                    }}
                >
                    Download One-Atom Data (CSV)
                </button>

            </div>


            {/* ========================================= */}
            {/* SCAFFOLD INFORMATION */}
            {/* ========================================= */}

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


            {/* ========================================= */}
            {/* ONE ATOM DIFFERENCE ANALYSIS */}
            {/* ========================================= */}

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

                    <b>Total Pairs Checked:</b>{" "}

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

                    <b>Valid One-Atom Pairs:</b>{" "}

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

                    <b>Strong Potential Cliffs:</b>{" "}

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

                    <b>Moderate Potential Cliffs:</b>{" "}

                    {
                        oneAtomAnalysis.moderate_cliffs
                        || 0
                    }

                </div>

            </div>


            {/* ========================================= */}
            {/* PAIRS TABLE */}
            {/* ========================================= */}

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

                                                <td style={{ padding: 12 }}>
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

                                                <td style={{ padding: 12 }}>
                                                    {
                                                        pair.molecule_1
                                                        ?.pic50
                                                    }
                                                </td>

                                                <td style={{ padding: 12 }}>
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

                                                <td style={{ padding: 12 }}>
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


            {/* ========================================= */}
            {/* MOLECULES */}
            {/* ========================================= */}

            <h2>
                Molecules
            </h2>


            <p>

                Total Molecules:{" "}

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