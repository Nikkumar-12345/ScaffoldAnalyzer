import { useLocation, Navigate, useNavigate } from "react-router-dom";

import SummaryCard from "../components/SummaryCard";
import CompositionChart from "../components/CompositionChart";
import ScaffoldCard from "../components/ScaffoldCard";

export default function Dashboard() {

    const location = useLocation();

    const navigate = useNavigate();

    const result = location.state?.result;

    if (!result) {

        return <Navigate to="/" />;

    }

    const summary = result.summary;

    const scaffolds = result.top_scaffolds;

    const chartData = result.charts.composition;

    function investigate(scaffold) {

        navigate("/scaffold", {

            state: {

                scaffold

            }

        });

    }

    return (

        <div

            style={{

                padding:40,

                background:"#0f172a",

                color:"white",

                minHeight:"100vh"

            }}

        >

            <h1>

                Scaffold Analyzer

            </h1>

            <br/>

            <div

                style={{

                    display:"grid",

                    gridTemplateColumns:"repeat(4,1fr)",

                    gap:20

                }}

            >

                <SummaryCard title="Protein" value={summary.protein} />

                <SummaryCard title="Gene" value={summary.gene} />

                <SummaryCard title="Target" value={summary.chembl_target} />

                <SummaryCard title="Activity Records" value={summary.activity_records} />

                <SummaryCard title="Unique Molecules" value={summary.unique_molecules} />

                <SummaryCard title="Unique Scaffolds" value={summary.unique_scaffolds} />

                <SummaryCard title="Largest Scaffold %" value={summary.largest_scaffold_percentage + "%"} />

                <SummaryCard title="Average pIC50" value={summary.average_pic50} />

            </div>

            <br/>
            <br/>

            <h2>

                Top 10 Scaffold Composition

            </h2>

            <CompositionChart

                data={chartData}

            />

            <br/>
            <br/>

            <h2>

                Top Ranked Scaffolds

            </h2>

            <div

                style={{

                    display:"grid",

                    gridTemplateColumns:"repeat(auto-fill,minmax(460px,1fr))",

                    gap:20

                }}

            >

                {

                    scaffolds.map(

                        scaffold => (

                            <ScaffoldCard

                                key={scaffold.id}

                                scaffold={scaffold}

                                onInvestigate={investigate}

                            />

                        )

                    )

                }

            </div>

        </div>

    );

}