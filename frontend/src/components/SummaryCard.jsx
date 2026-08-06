export default function SummaryCard({

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