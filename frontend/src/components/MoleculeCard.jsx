export default function MoleculeCard({ molecule }) {

    const descriptors = molecule.descriptors || {};

    const drug = molecule.druglikeness || {};

    return (

        <div

            style={{

                background:"#1e293b",

                padding:20,

                borderRadius:12,

                color:"white"

            }}

        >

            <div

                dangerouslySetInnerHTML={{

                    __html:molecule.svg

                }}

            />

            <hr/>

            <h3>

                {molecule.chembl_id}

            </h3>

            <p>

                <b>pIC50 :</b>

                {" "}

                {molecule.pic50}

            </p>

            <p>

                <b>Drug Score :</b>

                {" "}

                {drug.druglikeness_score}

            </p>

            <hr/>

            <p>

                <b>MW :</b>

                {" "}

                {descriptors.molecular_weight}

            </p>

            <p>

                <b>LogP :</b>

                {" "}

                {descriptors.logp}

            </p>

            <p>

                <b>TPSA :</b>

                {" "}

                {descriptors.tpsa}

            </p>

            <hr/>

            <p>

                <b>QED :</b>

                {" "}

                {descriptors.qed}

            </p>

            <p>

                <b>Lipinski :</b>

                {" "}

                {

                    drug.lipinski_pass

                    ?

                    "PASS"

                    :

                    "FAIL"

                }

            </p>

            <p>

                <b>Veber :</b>

                {" "}

                {

                    drug.veber_pass

                    ?

                    "PASS"

                    :

                    "FAIL"

                }

            </p>

            <hr/>

            <p>

                <b>SMILES</b>

            </p>

            <div

                style={{

                    wordBreak:"break-all",

                    fontSize:12

                }}

            >

                {molecule.smiles}

            </div>

        </div>

    );

}