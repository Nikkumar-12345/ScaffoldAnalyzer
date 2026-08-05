import { useLocation, Navigate } from "react-router-dom";

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer
} from "recharts";

export default function Dashboard() {

    const location = useLocation();

    const result = location.state?.result;

    if (!result) {
        return <Navigate to="/" />;
    }

    const summary = result.summary;

    const scaffolds = result.top_scaffolds;

    const chartData = result.chart_data;

    return (

        <div
            style={{
                padding: "40px",
                background: "#0f172a",
                minHeight: "100vh",
                color: "white"
            }}
        >

            <h1>

                Scaffold Analyzer

            </h1>

            <br />

            {/* SUMMARY */}

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(4,1fr)",
                    gap: "20px"
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
                    value={summary.largest_scaffold_percentage + "%"}
                />

                <SummaryCard
                    title="Target"
                    value={summary.chembl_target}
                />

                <SummaryCard
                    title="Invalid SMILES"
                    value={summary.invalid_smiles}
                />

            </div>

            <br />
            <br />

            <h2>

                Top 10 Scaffold Composition

            </h2>

            <div
                style={{
                    width: "100%",
                    height: 420,
                    background: "#1e293b",
                    padding: 20,
                    borderRadius: 12
                }}
            >

                <ResponsiveContainer>

                    <BarChart
                        data={chartData}
                    >

                        <CartesianGrid strokeDasharray="3 3" />

                        <XAxis
                            dataKey="name"
                        />

                        <YAxis />

                        <Tooltip />

                        <Bar
                            dataKey="percentage"
                        />

                    </BarChart>

                </ResponsiveContainer>

            </div>

            <br />
            <br />

            <h2>

                Top Scaffolds

            </h2>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill,minmax(430px,1fr))",
                    gap: "20px"
                }}
            >

                {

                    scaffolds.map(

                        (scaffold) => (

                            <div

                                key={scaffold.id}

                                style={{

                                    background: "#1e293b",

                                    borderRadius: 12,

                                    padding: 20

                                }}

                            >

                                <div

                                    dangerouslySetInnerHTML={{

                                        __html: scaffold.svg

                                    }}

                                />

                                <hr />

                                <p>

                                    <b>Scaffold ID :</b>

                                    {" "}

                                    SCF-{scaffold.id}

                                </p>

                                <p>

                                    <b>SMILES :</b>

                                    {" "}

                                    <span
                                        style={{
                                            wordBreak: "break-all"
                                        }}
                                    >

                                        {scaffold.scaffold_smiles}

                                    </span>

                                </p>

                                <p>

                                    <b>Occurrences :</b>

                                    {" "}

                                    {scaffold.occurrences}

                                </p>

                                <p>

                                    <b>Percentage :</b>

                                    {" "}

                                    {scaffold.percentage}%

                                </p>

                                <p>

                                    <b>Activity Records :</b>

                                    {" "}

                                    {scaffold.activity_records}

                                </p>

                                <p>

                                    <b>Unique Molecules :</b>

                                    {" "}

                                    {scaffold.unique_molecules}

                                </p>

                                <p>

                                    <b>Maximum pIC50 :</b>

                                    {" "}

                                    {scaffold.max_pic50}

                                </p>

                                <p>

                                    <b>Mean pIC50 :</b>

                                    {" "}

                                    {scaffold.mean_pic50}

                                </p>

                                <p>

                                    <b>Median pIC50 :</b>

                                    {" "}

                                    {scaffold.median_pic50}

                                </p>

                                <p>

                                    <b>Minimum pIC50 :</b>

                                    {" "}

                                    {scaffold.min_pic50}

                                </p>

                                <p>

                                    <b>Std Dev :</b>

                                    {" "}

                                    {scaffold.std_pic50}

                                </p>

                                <br />

                                <button>

                                    Investigate Scaffold

                                </button>

                            </div>

                        )

                    )

                }

            </div>

        </div>

    );

}

function SummaryCard({

    title,

    value

}) {

    return (

        <div

            style={{

                background: "#1e293b",

                padding: 20,

                borderRadius: 12,

                textAlign: "center"

            }}

        >

            <h3>

                {title}

            </h3>

            <h2>

                {value}

            </h2>

        </div>

    );

}