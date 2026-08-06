export default function ScaffoldCard({ scaffold, onInvestigate }) {
    const descriptors = scaffold.descriptors || {};
    const drug = scaffold.druglikeness || {};
    const ranking = scaffold.ranking || {};

    return (
        <div
            style={{
                background: "#1e293b",
                borderRadius: 12,
                padding: 20,
                color: "white"
            }}
        >
            <div
                dangerouslySetInnerHTML={{
                    __html: scaffold.svg
                }}
            />

            <hr />

            <h2>
                Rank #{scaffold.rank}
            </h2>

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

            <hr />

            <p>
                <b>Scaffold ID :</b>{" "}
                SCF-{scaffold.id}
            </p>

            <p>
                <b>SMILES :</b>{" "}
                <span
                    style={{
                        wordBreak: "break-all"
                    }}
                >
                    {scaffold.scaffold_smiles}
                </span>
            </p>

            <hr />

            <h3>Occurrence</h3>

            <p>
                <b>Occurrences :</b>{" "}
                {scaffold.occurrences}
            </p>

            <p>
                <b>Percentage :</b>{" "}
                {scaffold.percentage}%
            </p>

            <p>
                <b>Unique Molecules :</b>{" "}
                {scaffold.unique_molecules}
            </p>

            <p>
                <b>Activity Records :</b>{" "}
                {scaffold.activity_records}
            </p>

            <hr />

            <h3>Potency</h3>

            <p>
                <b>Maximum pIC50 :</b>{" "}
                {scaffold.max_pic50}
            </p>

            <p>
                <b>Mean pIC50 :</b>{" "}
                {scaffold.mean_pic50}
            </p>

            <p>
                <b>Median pIC50 :</b>{" "}
                {scaffold.median_pic50}
            </p>

            <p>
                <b>Minimum pIC50 :</b>{" "}
                {scaffold.min_pic50}
            </p>

            <p>
                <b>Std Dev :</b>{" "}
                {scaffold.std_pic50}
            </p>

            <hr />

            <h3>Drug-Likeness</h3>

            <p>
                <b>Drug Score :</b>{" "}
                {drug.druglikeness_score}
            </p>

            <p>
                <b>QED :</b>{" "}
                {descriptors.qed}
            </p>

            <p>
                <b>Lipinski :</b>{" "}
                {drug.lipinski_pass ? "PASS" : "FAIL"}
            </p>

            <p>
                <b>Veber :</b>{" "}
                {drug.veber_pass ? "PASS" : "FAIL"}
            </p>

            <hr />

            <h3>Physicochemical Properties</h3>

            <p>
                <b>Molecular Weight :</b>{" "}
                {descriptors.molecular_weight}
            </p>

            <p>
                <b>LogP :</b>{" "}
                {descriptors.logp}
            </p>

            <p>
                <b>TPSA :</b>{" "}
                {descriptors.tpsa}
            </p>

            <p>
                <b>HBA :</b>{" "}
                {descriptors.hba}
            </p>

            <p>
                <b>HBD :</b>{" "}
                {descriptors.hbd}
            </p>

            <p>
                <b>Rotatable Bonds :</b>{" "}
                {descriptors.rotatable_bonds}
            </p>

            <p>
                <b>Fraction Csp3 :</b>{" "}
                {descriptors.fsp3}
            </p>

            <hr />

            <h3>Complexity</h3>

            <p>
                <b>Bertz Complexity :</b>{" "}
                {descriptors.bertz_complexity}
            </p>

            <p>
                <b>Ring Count :</b>{" "}
                {descriptors.ring_count}
            </p>

            <p>
                <b>Aromatic Rings :</b>{" "}
                {descriptors.aromatic_rings}
            </p>

            <button
                style={{
                    marginTop: 20,
                    width: "100%",
                    padding: 12,
                    cursor: "pointer",
                    borderRadius: 8
                }}
                onClick={() => onInvestigate(scaffold)}
            >
                Investigate Scaffold
            </button>
        </div>
    );
}