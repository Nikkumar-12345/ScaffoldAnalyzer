import { useLocation, Navigate } from "react-router-dom";
import MoleculeCard from "../components/MoleculeCard";

export default function ScaffoldDetails() {

    const location = useLocation();

    const scaffold = location.state?.scaffold;

    if (!scaffold) {

        return <Navigate to="/dashboard" />;

    }

    const descriptors = scaffold.descriptors || {};

    const drug = scaffold.druglikeness || {};

    const ranking = scaffold.ranking || {};

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

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "350px 1fr",
                    gap: "40px",
                    alignItems: "start"
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

                        <b>Rank :</b> {scaffold.rank}

                    </p>

                    <p>

                        <b>Overall Score :</b> {ranking.overall_score}

                    </p>

                    <p>

                        <b>Grade :</b> {ranking.grade}

                    </p>

                    <p>

                        <b>Status :</b> {ranking.label}

                    </p>

                    <p>

                        <b>Scaffold SMILES :</b>

                    </p>

                    <div
                        style={{
                            wordBreak: "break-all",
                            marginBottom: 20
                        }}
                    >

                        {scaffold.scaffold_smiles}

                    </div>

                </div>

            </div>

            <br />

            <hr />

            <br />

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3,1fr)",
                    gap: 20
                }}
            >

                <div
                    style={{
                        background: "#1e293b",
                        padding: 20,
                        borderRadius: 12
                    }}
                >

                    <h3>

                        Potency

                    </h3>

                    <p>

                        Max pIC50 : {scaffold.max_pic50}

                    </p>

                    <p>

                        Mean pIC50 : {scaffold.mean_pic50}

                    </p>

                    <p>

                        Median pIC50 : {scaffold.median_pic50}

                    </p>

                    <p>

                        Min pIC50 : {scaffold.min_pic50}

                    </p>

                    <p>

                        Std Dev : {scaffold.std_pic50}

                    </p>

                </div>

                <div
                    style={{
                        background: "#1e293b",
                        padding: 20,
                        borderRadius: 12
                    }}
                >

                    <h3>

                        Drug Likeness

                    </h3>

                    <p>

                        Drug Score : {drug.druglikeness_score}

                    </p>

                    <p>

                        QED : {descriptors.qed}

                    </p>

                    <p>

                        Lipinski : {drug.lipinski_pass ? "PASS" : "FAIL"}

                    </p>

                    <p>

                        Veber : {drug.veber_pass ? "PASS" : "FAIL"}

                    </p>

                </div>
                <div
    style={{
        background: "#1e293b",
        padding: 20,
        borderRadius: 12
    }}
>

    <h3>

        Functional Groups

    </h3>

    <div
        style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 10,
            marginTop: 10
        }}
    >

        {
            scaffold.functional_groups &&
            scaffold.functional_groups.length > 0
                ? scaffold.functional_groups.map((group, index) => (

                    <span
                        key={index}
                        style={{
                            background: "#2563eb",
                            color: "white",
                            padding: "6px 12px",
                            borderRadius: 20,
                            fontSize: 13,
                            fontWeight: "bold"
                        }}
                    >
                        {group}
                    </span>

                ))
                : (
                    <span>

                        No Functional Groups Detected

                    </span>
                )
        }

    </div>

</div>

                <div
                    style={{
                        background: "#1e293b",
                        padding: 20,
                        borderRadius: 12
                    }}
                >

                    <h3>

                        Physicochemical

                    </h3>

                    <p>

                        MW : {descriptors.molecular_weight}

                    </p>

                    <p>

                        LogP : {descriptors.logp}

                    </p>

                    <p>

                        TPSA : {descriptors.tpsa}

                    </p>

                    <p>

                        HBA : {descriptors.hba}

                    </p>

                    <p>

                        HBD : {descriptors.hbd}

                    </p>

                    <p>

                        Rotatable Bonds : {descriptors.rotatable_bonds}

                    </p>

                    <p>

                        Fsp3 : {descriptors.fsp3}

                    </p>

                    <p>

                        Bertz Complexity : {descriptors.bertz_complexity}

                    </p>

                    <p>

                        Ring Count : {descriptors.ring_count}

                    </p>

                    <p>

                        Aromatic Rings : {descriptors.aromatic_rings}

                    </p>

                </div>

            </div>

            <br />

            <hr />

            <br />

            <h2>

                Molecules

            </h2>

            <p>

                Total Molecules : {scaffold.unique_molecules}

            </p>

            <br />

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill,minmax(340px,1fr))",
                    gap: 20
                }}
            >

                {

                    scaffold.molecules.map(

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