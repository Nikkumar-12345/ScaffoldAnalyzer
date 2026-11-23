import {
    ResponsiveContainer,
    BarChart,
    Bar,
    CartesianGrid,
    Tooltip,
    XAxis,
    YAxis
} from "recharts";

const AXIS = { fill: "#7c858e", fontSize: 12, fontFamily: "IBM Plex Mono, monospace" };

export default function CompositionChart({ data }) {

    return (

        <div className="chart-box">

            <ResponsiveContainer>

                <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>

                    <CartesianGrid stroke="#262d35" vertical={false} />

                    <XAxis
                        dataKey="name"
                        tick={AXIS}
                        tickLine={false}
                        axisLine={{ stroke: "#38414b" }}
                    />

                    <YAxis
                        tick={AXIS}
                        tickLine={false}
                        axisLine={false}
                        unit="%"
                    />

                    <Tooltip
                        cursor={{ fill: "rgba(217,164,65,0.08)" }}
                        contentStyle={{
                            background: "#1a1f25",
                            border: "1px solid #38414b",
                            borderRadius: 4,
                            color: "#e8e6e1",
                            fontSize: 13
                        }}
                        labelStyle={{ color: "#b4b9bf" }}
                        formatter={value => [`${value}%`, "Share of molecules"]}
                    />

                    <Bar dataKey="percentage" fill="#d9a441" radius={[2, 2, 0, 0]} />

                </BarChart>

            </ResponsiveContainer>

        </div>

    );
}
