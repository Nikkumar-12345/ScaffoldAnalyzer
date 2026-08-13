// removed unused recharts imports
import { useEffect, useState } from "react";
import { useLocation, Navigate } from "react-router-dom";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer
} from "recharts";

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
            setMolecules(res.data.molecules);
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

    const descriptors = scaffold.descriptors || {};

    const drug = scaffold.druglikeness || {};

    const ranking = scaffold.ranking || {};
    const sideChainAnalysis =
    scaffold.side_chain_analysis || {};

const sideChains =
    sideChainAnalysis.side_chains || [];

const highestActivity =
    sideChainAnalysis.highest_activity;

const lowestActivity =
    sideChainAnalysis.lowest_activity;

    return (

        <div
            style={{
                background:"#0f172a",
                color:"white",
                minHeight:"100vh",
                padding:"40px"
            }}
        >

            <h1>

                Scaffold Details

            </h1>

            <br/>

            <div
                style={{
                    display:"grid",
                    gridTemplateColumns:"350px 1fr",
                    gap:"40px"
                }}
            >

                <div
                    style={{
                        background:"#1e293b",
                        padding:20,
                        borderRadius:12
                    }}
                >

                    <div
                        dangerouslySetInnerHTML={{
                            __html:scaffold.svg
                        }}
                    />

                </div>

                <div>

                    <h2>

                        Scaffold Information

                    </h2>

                    <p>

                        <b>Rank :</b>

                        {scaffold.rank}

                    </p>

                    <p>

                        <b>Overall Score :</b>

                        {ranking.overall_score}

                    </p>

                    <p>

                        <b>Grade :</b>

                        {ranking.grade}

                    </p>

                    <p>

                        <b>Status :</b>

                        {ranking.label}

                    </p>

                    <p>

                        <b>Drug Score :</b>

                        {drug.druglikeness_score}

                    </p>

                    <p>

                        <b>QED :</b>

                        {descriptors.qed}

                    </p>

                </div>

            </div>

            <br/>

            <hr/>

            <br/>
            <hr />

<br />

<h2>

    Side Chain Analysis

</h2>

<br />

<div
    style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit,minmax(300px,1fr))",
        gap: 20
    }}
>

    {/* Highest Activity */}

    <div
        style={{
            background: "#1e293b",
            padding: 20,
            borderRadius: 12
        }}
    >

        <h3>

            Highest pIC50

        </h3>

        {

            highestActivity

            ?

            <>

                <p>

                    <b>pIC50 :</b>{" "}

                    {highestActivity.pic50}

                </p>

                <p>

                    <b>ChEMBL ID :</b>{" "}

                    {highestActivity.chembl_id}

                </p>

                <p>

                    <b>Side Chain :</b>

                </p>

                <div
                    style={{
                        wordBreak: "break-all",
                        fontSize: 13
                    }}
                >

                    {highestActivity.side_chain}

                </div>

            </>

            :

            <p>No data available</p>

        }

    </div>


    {/* Lowest Activity */}

    <div
        style={{
            background: "#1e293b",
            padding: 20,
            borderRadius: 12
        }}
    >

        <h3>

            Lowest pIC50

        </h3>

        {

            lowestActivity

            ?

            <>

                <p>

                    <b>pIC50 :</b>{" "}

                    {lowestActivity.pic50}

                </p>

                <p>

                    <b>ChEMBL ID :</b>{" "}

                    {lowestActivity.chembl_id}

                </p>

                <p>

                    <b>Side Chain :</b>

                </p>

                <div
                    style={{
                        wordBreak: "break-all",
                        fontSize: 13
                    }}
                >

                    {lowestActivity.side_chain}

                </div>

            </>

            :

            <p>No data available</p>

        }

    </div>


    {/* Activity Cliff */}

    <div
        style={{
            background: sideChainAnalysis.possible_activity_cliff
                ? "#7f1d1d"
                : "#1e293b",

            padding: 20,

            borderRadius: 12
        }}
    >

        <h3>

            Activity Cliff Analysis

        </h3>

        <p>

            <b>pIC50 Difference :</b>{" "}

            {sideChainAnalysis.activity_difference}

        </p>

        <p>

            <b>Status :</b>{" "}

            {

                sideChainAnalysis.possible_activity_cliff

                ?

                "POSSIBLE ACTIVITY CLIFF"

                :

                "NO STRONG CLIFF"

            }

        </p>

        <p>

            {sideChainAnalysis.message}

        </p>

    </div>

</div>


<br />

<div
    style={{
        background: "#1e293b",
        padding: 20,
        borderRadius: 12
    }}
>

    <h3>

        Side Chain vs Maximum pIC50

    </h3>

    <div
        style={{
            width: "100%",
            height: 450
        }}
    >

        <ResponsiveContainer
            width="100%"
            height="100%"
        >

            <BarChart
                data={sideChains}
            >

                <XAxis
                    dataKey="side_chain"
                    tick={{
                        fill: "white",
                        fontSize: 10
                    }}
                    interval={0}
                    angle={-35}
                    textAnchor="end"
                    height={130}
                />

                <YAxis
                    tick={{
                        fill: "white"
                    }}
                />

                <Tooltip />

                <Bar
                    dataKey="max_pic50"
                    name="Maximum pIC50"
                />

            </BarChart>

        </ResponsiveContainer>

    </div>

</div>


<br />


<h3>

    Side Chain Statistics

</h3>

<div
    style={{
        overflowX: "auto"
    }}
>

    <table
        style={{
            width: "100%",
            borderCollapse: "collapse",
            background: "#1e293b"
        }}
    >

        <thead>

            <tr>

                <th>Side Chain</th>

                <th>Count</th>

                <th>Min pIC50</th>

                <th>Mean pIC50</th>

                <th>Max pIC50</th>

            </tr>

        </thead>

        <tbody>

            {

                sideChains.map(
                    (chain, index) => (

                        <tr key={index}>

                            <td
                                style={{
                                    padding: 12,
                                    wordBreak: "break-all"
                                }}
                            >

                                {chain.side_chain}

                            </td>

                            <td>{chain.count}</td>

                            <td>{chain.min_pic50}</td>

                            <td>{chain.mean_pic50}</td>

                            <td>{chain.max_pic50}</td>

                        </tr>

                    )
                )

            }

        </tbody>

    </table>

</div>

<br />

            <h2>

                Molecules

            </h2>

            <p>

                Total Molecules :

                {" "}

                {scaffold.unique_molecules}

            </p>

            <br/>

            {

                loading &&

                <h2>

                    Loading Molecules...

                </h2>

            }

            <div
                style={{
                    display:"grid",
                    gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))",
                    gap:20
                }}
            >

                {

                    molecules.map(

                        (molecule,index)=>(

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