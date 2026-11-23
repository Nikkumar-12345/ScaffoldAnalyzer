import { useEffect, useMemo, useState } from "react";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    Cell,
    CartesianGrid,
    ReferenceLine,
    Tooltip,
    XAxis,
    YAxis
} from "recharts";

import api from "../services/api";


/*
 * Extra views on the one-atom difference results. The numbers come from
 * the existing analysis; nothing here recomputes it. The backend returns
 * the largest-change pairs (up to 50 per scaffold), so charts and the
 * "most frequent changes" list describe those listed pairs, while the
 * bars for cliff share and change type use the full counts.
 */

const AXIS = { fill: "#7c858e", fontSize: 11, fontFamily: "IBM Plex Mono, monospace" };

const COLORS = { strong: "#d9534f", moderate: "#d9a441", low: "#4b5560" };


function level(delta) {

    if (delta >= 2) return "strong";
    if (delta >= 1) return "moderate";
    return "low";
}


function SplitBar({ title, parts }) {

    const total = parts.reduce((sum, part) => sum + part.value, 0);

    return (

        <div className="oa-split">

            <div className="oa-split-title">{title}</div>

            <div className="oa-bar" role="img" aria-label={title}>
                {parts.map(part => (
                    total > 0 && part.value > 0 && (
                        <span
                            key={part.label}
                            style={{
                                width: `${100 * part.value / total}%`,
                                background: part.color
                            }}
                            title={`${part.label}: ${part.value}`}
                        />
                    )
                ))}
            </div>

            <div className="oa-legend">
                {parts.map(part => (
                    <span key={part.label}>
                        <i style={{ background: part.color }} />
                        {part.label}{" "}
                        <b className="mono">{part.value.toLocaleString("en-US")}</b>
                        {total > 0 && (
                            <em> {(100 * part.value / total).toFixed(0)}%</em>
                        )}
                    </span>
                ))}
            </div>

        </div>
    );
}


function PairDetail({ pair, scaffold }) {

    const [data, setData] = useState(null);
    const [error, setError] = useState("");

    useEffect(() => {

        let cancelled = false;

        const wanted = [pair.molecule_1?.chembl_id, pair.molecule_2?.chembl_id];

        const batch = (scaffold.molecules || []).filter(
            m => wanted.includes(m.chembl_id)
        );

        api.post("/scaffold/details", { molecules: batch })
            .then(response => {
                if (!cancelled) setData(response.data.molecules || []);
            })
            .catch(() => {
                if (!cancelled) setError("Could not draw these molecules.");
            });

        return () => { cancelled = true; };

    }, [pair, scaffold]);

    const byId = Object.fromEntries((data || []).map(m => [m.chembl_id, m]));

    return (

        <div className="oa-pair">

            {error && <p className="mcs-error">{error}</p>}

            {!data && !error && <p>Drawing…</p>}

            {data && [pair.molecule_1, pair.molecule_2].map((m, index) => (

                <figure key={index} className="stereo-isomer">

                    {byId[m?.chembl_id]
                        ? <div dangerouslySetInnerHTML={{
                            __html: byId[m.chembl_id].svg
                        }} />
                        : <p>No drawing</p>}

                    <figcaption>
                        <strong>{m?.chembl_id}</strong>
                        <br />
                        pIC50 {m?.pic50}
                    </figcaption>

                </figure>

            ))}

            <div className="oa-change">
                <span className="oa-change-label">Change</span>
                <strong>{pair.structural_change}</strong>
                <span className="oa-change-label">ΔpIC50</span>
                <strong className="mono">{pair.delta_pic50}</strong>
                <span className="oa-note">
                    {Number(pair.delta_pic50) >= 1
                        ? `${(10 ** pair.delta_pic50).toFixed(0)}-fold change in potency`
                        : "Less than a 10-fold change in potency"}
                </span>
            </div>

        </div>
    );
}


export default function OneAtomPanel({ analysis, pairs, scaffold }) {

    const [filter, setFilter] = useState("all");
    const [kind, setKind] = useState("all");
    const [query, setQuery] = useState("");
    const [direction, setDirection] = useState("desc");
    const [openRow, setOpenRow] = useState(null);

    const valid = analysis.valid_one_atom_pairs || 0;
    const strong = analysis.strong_cliffs || 0;
    const moderate = analysis.moderate_cliffs || 0;

    const kinds = useMemo(
        () => [...new Set(pairs.map(p => p.change_type).filter(Boolean))],
        [pairs]
    );

    const frequent = useMemo(() => {

        const groups = {};

        for (const pair of pairs) {

            const key = pair.structural_change;

            if (!key) continue;

            groups[key] = groups[key] || { change: key, count: 0, total: 0 };

            groups[key].count += 1;
            groups[key].total += Number(pair.delta_pic50) || 0;
        }

        return Object.values(groups)
            .sort((a, b) => b.count - a.count || b.total - a.total)
            .slice(0, 6);

    }, [pairs]);

    const chartData = useMemo(
        () => pairs.map((pair, index) => ({
            n: index + 1,
            delta: Number(pair.delta_pic50),
            label: pair.structural_change
        })),
        [pairs]
    );

    const visible = useMemo(() => {

        const text = query.trim().toLowerCase();

        return pairs
            .map((pair, index) => ({ pair, index }))
            .filter(({ pair }) =>
                filter === "all" || level(pair.delta_pic50) === filter
            )
            .filter(({ pair }) => kind === "all" || pair.change_type === kind)
            .filter(({ pair }) => !text
                || pair.molecule_1?.chembl_id?.toLowerCase().includes(text)
                || pair.molecule_2?.chembl_id?.toLowerCase().includes(text)
                || (pair.structural_change || "").toLowerCase().includes(text))
            .sort((a, b) => direction === "desc"
                ? b.pair.delta_pic50 - a.pair.delta_pic50
                : a.pair.delta_pic50 - b.pair.delta_pic50);

    }, [pairs, filter, kind, query, direction]);

    if (valid === 0 && pairs.length === 0) {
        return null;
    }

    return (

        <div className="oa">

            <div className="oa-splits">

                <SplitBar
                    title="Potency effect of one-atom changes (all valid pairs)"
                    parts={[
                        { label: "Strong ≥ 2", value: strong, color: COLORS.strong },
                        { label: "Moderate 1 to 2", value: moderate, color: COLORS.moderate },
                        {
                            label: "Below 1",
                            value: Math.max(valid - strong - moderate, 0),
                            color: COLORS.low
                        }
                    ]}
                />

                <SplitBar
                    title="Kind of change (all valid pairs)"
                    parts={[
                        {
                            label: "Replacement",
                            value: analysis.replacement_pairs || 0,
                            color: "#6aa7c9"
                        },
                        {
                            label: "Addition / removal",
                            value: analysis.addition_removal_pairs || 0,
                            color: "#9b8fd0"
                        }
                    ]}
                />

            </div>

            {pairs.length > 0 && (

                <div className="oa-grid">

                    <div className="oa-chart">

                        <div className="oa-split-title">
                            ΔpIC50 of the {pairs.length} listed pairs
                            {valid > pairs.length
                                && ` (largest of ${valid.toLocaleString("en-US")})`}
                        </div>

                        <div className="oa-chart-box">

                            <ResponsiveContainer>

                                <BarChart
                                    data={chartData}
                                    margin={{ top: 6, right: 6, left: -18, bottom: 0 }}
                                >

                                    <CartesianGrid stroke="#262d35" vertical={false} />

                                    <XAxis dataKey="n" tick={AXIS} tickLine={false} />

                                    <YAxis tick={AXIS} tickLine={false} axisLine={false} />

                                    <ReferenceLine y={2} stroke={COLORS.strong} strokeDasharray="4 3" />
                                    <ReferenceLine y={1} stroke={COLORS.moderate} strokeDasharray="4 3" />

                                    <Tooltip
                                        cursor={{ fill: "rgba(255,255,255,0.05)" }}
                                        contentStyle={{
                                            background: "#1a1f25",
                                            border: "1px solid #38414b",
                                            borderRadius: 4,
                                            fontSize: 12
                                        }}
                                        formatter={(value, _name, item) => [
                                            value, item.payload.label
                                        ]}
                                        labelFormatter={n => `Pair ${n}`}
                                    />

                                    <Bar dataKey="delta" radius={[2, 2, 0, 0]}>
                                        {chartData.map(row => (
                                            <Cell
                                                key={row.n}
                                                fill={COLORS[level(row.delta)]}
                                            />
                                        ))}
                                    </Bar>

                                </BarChart>

                            </ResponsiveContainer>

                        </div>

                    </div>

                    <div className="oa-frequent">

                        <div className="oa-split-title">
                            Most frequent changes among the listed pairs
                        </div>

                        <table className="oa-mini">
                            <thead>
                                <tr><th>Change</th><th>Pairs</th><th>Mean Δ</th></tr>
                            </thead>
                            <tbody>
                                {frequent.map(row => (
                                    <tr key={row.change}>
                                        <td>{row.change}</td>
                                        <td className="mono">{row.count}</td>
                                        <td className="mono">
                                            {(row.total / row.count).toFixed(2)}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>

                    </div>

                </div>

            )}

            {pairs.length > 0 && (

                <>
                    <div className="oa-controls">

                        <div className="oa-chips">
                            {[
                                ["all", "All"],
                                ["strong", "Strong"],
                                ["moderate", "Moderate"],
                                ["low", "Below 1"]
                            ].map(([key, label]) => (
                                <button
                                    key={key}
                                    className={"chip" + (filter === key ? " chip-on" : "")}
                                    onClick={() => setFilter(key)}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>

                        <select value={kind} onChange={e => setKind(e.target.value)}>
                            <option value="all">All changes</option>
                            {kinds.map(k => <option key={k} value={k}>{k}</option>)}
                        </select>

                        <select
                            value={direction}
                            onChange={e => setDirection(e.target.value)}
                        >
                            <option value="desc">Largest Δ first</option>
                            <option value="asc">Smallest Δ first</option>
                        </select>

                        <input
                            className="text-input oa-search"
                            type="search"
                            placeholder="Molecule id or change (e.g. F)"
                            value={query}
                            onChange={e => setQuery(e.target.value)}
                        />

                    </div>

                    <p className="homolog-intro">
                        Showing {visible.length} of {pairs.length} listed pairs.
                        Click a pair to see both molecules side by side.
                    </p>

                    <div className="homolog-table-wrap">

                        <table className="homolog-table">

                            <thead>
                                <tr>
                                    <th>Pair</th>
                                    <th>Molecule 1</th>
                                    <th>pIC50 1</th>
                                    <th>Molecule 2</th>
                                    <th>pIC50 2</th>
                                    <th>Change</th>
                                    <th>ΔpIC50</th>
                                    <th>Result</th>
                                </tr>
                            </thead>

                            <tbody>

                                {visible.map(({ pair, index }) => (

                                    <PairRows
                                        key={index}
                                        pair={pair}
                                        index={index}
                                        scaffold={scaffold}
                                        open={openRow === index}
                                        onToggle={() =>
                                            setOpenRow(openRow === index ? null : index)}
                                    />

                                ))}

                            </tbody>

                        </table>

                    </div>
                </>

            )}

        </div>
    );
}


function PairRows({ pair, index, scaffold, open, onToggle }) {

    const kind = level(pair.delta_pic50);

    return (

        <>
            <tr className={`mcs-row oa-row-${kind}`} onClick={onToggle}>

                <td>{open ? "▾" : "▸"} {index + 1}</td>
                <td>{pair.molecule_1?.chembl_id}</td>
                <td className="mono">{pair.molecule_1?.pic50}</td>
                <td>{pair.molecule_2?.chembl_id}</td>
                <td className="mono">{pair.molecule_2?.pic50}</td>
                <td><strong>{pair.structural_change}</strong></td>
                <td className="mono"><strong>{pair.delta_pic50}</strong></td>
                <td>{pair.cliff_type}</td>

            </tr>

            {open && (

                <tr className="mcs-detail">
                    <td colSpan={8}>
                        <PairDetail pair={pair} scaffold={scaffold} />
                    </td>
                </tr>

            )}
        </>
    );
}
