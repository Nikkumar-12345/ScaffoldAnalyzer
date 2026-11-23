import { useState } from "react";

import api, { API_BASE_URL, getErrorMessage } from "../services/api";


/*
 * Stereochemistry: molecules that are the same flat structure but differ
 * in 3D arrangement (enantiomers, diastereomers, E/Z isomers).
 *
 * Nothing is requested until the user presses the button. The groups are
 * precomputed on the server, so pressing the button is a lookup.
 */

const PAGE = 25;


function fixed(value, digits = 2) {

    return value === null || value === undefined
        ? "-"
        : Number(value).toFixed(digits);
}


function fold(value) {

    if (value === null || value === undefined) {
        return "-";
    }

    return value >= 100
        ? `${Math.round(value)}x`
        : `${Number(value).toFixed(1)}x`;
}


function CliffBadge({ level }) {

    if (!level) {
        return <span className="stereo-badge stereo-badge-none">-</span>;
    }

    return (
        <span className={`stereo-badge stereo-badge-${level}`}>
            {level === "strong" ? "Strong" : "Moderate"}
        </span>
    );
}


function GroupRow({ uniprot, group }) {

    const [open, setOpen] = useState(false);
    const [detail, setDetail] = useState(null);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    async function toggle() {

        const next = !open;

        setOpen(next);

        if (!next || detail || loading) {
            return;
        }

        setLoading(true);
        setError("");

        try {

            const response = await api.post("/stereo/groups/detail", {
                uniprot_id: uniprot,
                group_no: group.group_no
            });

            setDetail(response.data);

        } catch (err) {

            setError(getErrorMessage(err, "Could not load this group."));

        } finally {

            setLoading(false);
        }
    }

    return (

        <>
            <tr className="mcs-row" onClick={toggle}>

                <td>{open ? "▾" : "▸"} {group.group_id}</td>
                <td>{group.relationship || "-"}</td>
                <td>{group.isomers}</td>
                <td>{fixed(group.pic50_best)}</td>
                <td>{fixed(group.pic50_worst)}</td>
                <td><strong>{fixed(group.delta_pic50)}</strong></td>
                <td>{fold(group.fold_change)}</td>
                <td><CliffBadge level={group.cliff} /></td>

            </tr>

            {open && (

                <tr className="mcs-detail">
                    <td colSpan={8}>

                        {loading && <p>Loading…</p>}

                        {error && <p className="mcs-error">{error}</p>}

                        {detail && (

                            <div className="stereo-isomers">

                                {detail.isomer_list.map((isomer, index) => (

                                    <figure
                                        key={isomer.chembl_id}
                                        className={
                                            "stereo-isomer"
                                            + (index === 0
                                                ? " stereo-isomer-best"
                                                : "")
                                        }
                                    >
                                        <div
                                            dangerouslySetInnerHTML={{
                                                __html: isomer.svg || ""
                                            }}
                                        />
                                        <figcaption>
                                            <strong>{isomer.chembl_id}</strong>
                                            <br />
                                            {isomer.stereo || "-"}
                                            <br />
                                            pIC50 {fixed(isomer.pic50)}
                                            {isomer.delta_from_best > 0
                                                && ` (−${fixed(isomer.delta_from_best)})`}
                                            {index === 0 && " ★ most potent"}
                                        </figcaption>
                                    </figure>

                                ))}

                            </div>

                        )}

                    </td>
                </tr>

            )}
        </>
    );
}


export default function StereoPanel({ uniprot }) {

    const [data, setData] = useState(null);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [minDelta, setMinDelta] = useState(0);

    async function load(offset, append, delta = minDelta) {

        setLoading(true);
        setError("");

        try {

            const response = await api.post("/stereo/groups", {
                uniprot_id: uniprot,
                offset,
                limit: PAGE,
                min_delta: delta
            });

            setData(previous =>
                append && previous
                    ? {
                        ...response.data,
                        groups: [
                            ...previous.groups,
                            ...response.data.groups
                        ]
                    }
                    : response.data
            );

        } catch (err) {

            setError(getErrorMessage(
                err,
                "Could not load the stereochemistry analysis."
            ));

        } finally {

            setLoading(false);
        }
    }

    const summary = data?.summary;

    const percent = summary && summary.molecules
        ? Math.round(100 * summary.with_stereocentres / summary.molecules)
        : 0;

    return (

        <div className="homolog-panel">

            <h2>Stereochemistry</h2>

            <p className="homolog-intro">
                Finds molecules that are the same flat structure but differ in
                3D arrangement (enantiomers, diastereomers, E/Z isomers) and
                shows how much their potency differs. Scaffold grouping cannot
                see these differences, yet one mirror image can be orders of
                magnitude more potent than the other. Results are precomputed,
                so this loads instantly.
            </p>

            {!data && (

                <button
                    className="mcs-button"
                    onClick={() => load(0, false)}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Show stereoisomer analysis"}
                </button>

            )}

            {error && <div className="homolog-empty">{error}</div>}

            {data && (

                <>
                    <div className="homolog-stats">

                        {[
                            ["Molecules", summary.molecules],
                            ["With stereocentres", `${percent}%`],
                            ["Fully defined", summary.fully_specified],
                            ["Isomer groups", summary.groups_total],
                            ["Enantiomer pairs", summary.enantiomer_pairs],
                            ["Cliffs ≥ 1 log", summary.cliffs_moderate],
                            ["Cliffs ≥ 2 log", summary.cliffs_strong]
                        ].map(([label, value]) => (
                            <div className="homolog-stat" key={label}>
                                <span className="homolog-stat-value">
                                    {value}
                                </span>
                                <span className="homolog-stat-label">
                                    {label}
                                </span>
                            </div>
                        ))}

                    </div>

                    <div className="mcs-toolbar">

                        <label>
                            Minimum ΔpIC50{" "}
                            <select
                                value={minDelta}
                                onChange={event => {
                                    const value = Number(event.target.value);
                                    setMinDelta(value);
                                    load(0, false, value);
                                }}
                            >
                                <option value={0}>All groups</option>
                                <option value={1}>≥ 1 (10-fold)</option>
                                <option value={2}>≥ 2 (100-fold)</option>
                            </select>
                        </label>

                        <a
                            className="mcs-button mcs-link"
                            href={`${API_BASE_URL}/stereo/csv/${uniprot}`}
                        >
                            Download CSV
                        </a>

                    </div>

                    {data.groups.length === 0 ? (

                        <div className="homolog-empty">
                            No stereoisomer groups with measured potency for
                            this target.
                        </div>

                    ) : (

                        <div className="homolog-table-wrap">
                            <table className="homolog-table mcs-table">
                                <thead>
                                    <tr>
                                        <th>Group</th>
                                        <th>Relationship</th>
                                        <th>Isomers</th>
                                        <th>Best pIC50</th>
                                        <th>Worst pIC50</th>
                                        <th>ΔpIC50</th>
                                        <th>Fold</th>
                                        <th>Cliff</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.groups.map(group => (
                                        <GroupRow
                                            key={group.group_no}
                                            uniprot={uniprot}
                                            group={group}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>

                    )}

                    {data.groups.length < data.matching && (

                        <button
                            className="mcs-button"
                            onClick={() => load(data.groups.length, true)}
                            disabled={loading}
                        >
                            {loading
                                ? "Loading…"
                                : `Show more (${data.matching - data.groups.length} left)`}
                        </button>

                    )}
                </>

            )}

        </div>
    );
}
