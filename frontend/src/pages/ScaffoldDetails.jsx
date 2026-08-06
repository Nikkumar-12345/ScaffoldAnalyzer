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