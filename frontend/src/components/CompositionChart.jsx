import {

    ResponsiveContainer,

    BarChart,

    Bar,

    CartesianGrid,

    Tooltip,

    XAxis,

    YAxis

} from "recharts";

export default function CompositionChart({

    data

}) {

    return (

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

                    data={data}

                >

                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis dataKey="name" />

                    <YAxis />

                    <Tooltip />

                    <Bar dataKey="percentage" />

                </BarChart>

            </ResponsiveContainer>

        </div>

    );

}