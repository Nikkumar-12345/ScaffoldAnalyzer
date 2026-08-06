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

                <b>pIC50 :</b> {molecule.pic50}

            </p>

            <p>

                <b>Drug Score :</b> {drug.druglikeness_score}

            </p>

            <hr/>

            <p><b>MW :</b> {descriptors.molecular_weight}</p>

            <p><b>LogP :</b> {descriptors.logp}</p>

            <p><b>TPSA :</b> {descriptors.tpsa}</p>

            <p><b>HBA :</b> {descriptors.hba}</p>

            <p><b>HBD :</b> {descriptors.hbd}</p>

            <p><b>Rotatable Bonds :</b> {descriptors.rotatable_bonds}</p>

            <p><b>QED :</b> {descriptors.qed}</p>

            <p>

                <b>Lipinski :</b>

                {drug.lipinski_pass ? " PASS" : " FAIL"}

            </p>

            <p>

                <b>Veber :</b>

                {drug.veber_pass ? " PASS" : " FAIL"}

            </p>

            <hr/>

            <h4>

                Functional Groups

            </h4>

            <div
                style={{
                    display:"flex",
                    flexWrap:"wrap",
                    gap:8,
                    marginBottom:15
                }}
            >

                {

                    molecule.functional_groups?.length

                    ?

                    molecule.functional_groups.map(

                        (group,index)=>(

                            <span

                                key={index}

                                style={{

                                    background:"#2563eb",

                                    padding:"5px 12px",

                                    borderRadius:20,

                                    fontSize:12

                                }}

                            >

                                {group}

                            </span>

                        )

                    )

                    :

                    <span>

                        None

                    </span>

                }

            </div>

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