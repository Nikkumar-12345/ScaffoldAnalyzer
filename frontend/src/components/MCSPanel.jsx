import { useState } from "react";

import api, { API_BASE_URL, getErrorMessage } from "../services/api";


/*
 * Chemical series and maximum common substructure (MCS).
 *
 * Nothing is requested until the user presses the button, so the rest
 * of the dashboard is unaffected. The series are precomputed on the
 * server (clustering plus an MCS search is too slow to run while a
 * user waits), so pressing the button is a lookup and returns at once.
 */

const PAGE = 25;


function fixed(value, digits = 2) {

    return value === null || value === undefined
        ? "-"
        : Number(value).toFixed(digits);
}


function SeriesRow({ uniprot, series }) {

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

            const response = await api.post("/mcs/series/detail", {
                uniprot_id: uniprot,
                series_no: series.series_no
            });

            setDetail(response.data);

        } catch (err) {

            setError(getErrorMessage(err, "Could not load this series."));

        } finally {

            setLoading(false);
        }
    }

    return (

        <>
            <tr className="mcs-row" onClick={toggle}>

                <td>{open ? "▾" : "▸"} {series.chemical_series_id}</td>
                <td>{series.number_of_molecules}</td>
                <td>{series.scaffolds_in_series}</td>
                <td>
                    {series.mcs_status === "single_molecule_series"
                        ? "single molecule"
                        : series.mcs_status}
                </td>
                <td>{series.mcs_atoms ?? "-"}</td>
                <td>{fixed(series.activity.median_pic50)}</td>
                <td className="mcs-smarts" title={series.mcs_smarts || ""}>
                    {series.mcs_smarts || "-"}
                </td>

            </tr>

            {open && (

                <tr className="mcs-detail">
                    <td colSpan={7}>

                        {loading && <p>Loading…</p>}

                        {error && <p className="mcs-error">{error}</p>}

                        {detail && (

                            <div className="mcs-detail-body">

                                <div className="mcs-images">

                                    {detail.mcs_svg && (
                                        <figure>
                                            <div
                                                dangerouslySetInnerHTML={{
                                                    __html: detail.mcs_svg
                                                }}
                                            />
                                            <figcaption>
                                                Common substructure
                                                {detail.mcs_coverage !== null
                                                    && ` (${fixed(detail.mcs_coverage, 0)}% of series)`}
                                            </figcaption>
                                        </figure>
                                    )}

                                    {detail.representative_svg && (
                                        <figure>
                                            <div
                                                dangerouslySetInnerHTML={{
                                                    __html:
                                                        detail.representative_svg
                                                }}
                                            />
                                            <figcaption>
                                                {detail.representative.chembl_id}
                                                {" "}with core highlighted
                                            </figcaption>
                                        </figure>
                                    )}

                                </div>

                                <div className="homolog-table-wrap">
                                    <table className="homolog-table">
                                        <thead>
                                            <tr>
                                                <th>Molecule</th>
                                                <th>pIC50</th>
                                                <th>SMILES</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {detail.molecules.map(m => (
                                                <tr key={m.chembl_id}>
                                                    <td>{m.chembl_id}</td>
                                                    <td>{fixed(m.pic50)}</td>
                                                    <td className="mcs-smarts">
                                                        {m.smiles}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>

                                {detail.number_of_molecules >
                                    detail.molecules.length && (
                                    <p className="homolog-intro">
                                        Showing the first{" "}
                                        {detail.molecules.length} of{" "}
                                        {detail.number_of_molecules} molecules
                                        (most potent first).
                                    </p>
                                )}

                            </div>

                        )}

                    </td>
                </tr>

            )}
        </>
    );
}


export default function MCSPanel({ uniprot }) {

    const [data, setData] = useState(null);
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);
    const [multiOnly, setMultiOnly] = useState(true);

    async function load(offset, append) {

        setLoading(true);
        setError("");

        try {

            const response = await api.post("/mcs/series", {
                uniprot_id: uniprot,
                offset,
                limit: PAGE,
                min_size: multiOnly ? 2 : 1
            });

            setData(previous =>
                append && previous
                    ? {
                        ...response.data,
                        series: [
                            ...previous.series,
                            ...response.data.series
                        ]
                    }
                    : response.data
            );

        } catch (err) {

            setError(getErrorMessage(
                err,
                "Could not load the chemical series."
            ));

        } finally {

            setLoading(false);
        }
    }

    const summary = data?.summary;

    return (

        <div className="homolog-panel">

            <h2>Chemical Series &amp; Maximum Common Substructure</h2>

            <p className="homolog-intro">
                Groups the molecules into chemical series by structural
                similarity (Morgan fingerprints, Tanimoto ≥ 0.6) and finds
                the core substructure every member of a series shares.
                Unlike scaffold grouping, which needs an exact match, this
                recovers the series a chemist would recognise. Results are
                precomputed, so this loads instantly.
            </p>

            {!data && (

                <button
                    className="mcs-button"
                    onClick={() => load(0, false)}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Show chemical series"}
                </button>

            )}

            {error && <div className="homolog-empty">{error}</div>}

            {data && (

                <>
                    <div className="homolog-stats">

                        {[
                            ["Series", summary.series_total],
                            ["Multi-molecule", summary.series_total
                                - summary.singletons],
                            ["Single molecule", summary.singletons],
                            ["Largest series", summary.largest_series],
                            ["MCS found", summary.mcs_success],
                            ["MCS timed out", summary.mcs_timeout]
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

                    {summary.truncated && (
                        <p className="homolog-intro">
                            This target has more molecules than can be
                            clustered; the most potent {summary.molecules_clustered}
                            {" "}were used.
                        </p>
                    )}

                    <div className="mcs-toolbar">

                        <label>
                            <input
                                type="checkbox"
                                checked={multiOnly}
                                onChange={event => {
                                    setMultiOnly(event.target.checked);
                                    setData(null);
                                }}
                            />
                            {" "}Hide single-molecule series
                        </label>

                        <a
                            className="mcs-button mcs-link"
                            href={`${API_BASE_URL}/mcs/csv/${uniprot}`}
                        >
                            Download CSV
                        </a>

                    </div>

                    {data.series.length === 0 ? (

                        <div className="homolog-empty">
                            No multi-molecule series for this target.
                        </div>

                    ) : (

                        <div className="homolog-table-wrap">
                            <table className="homolog-table mcs-table">
                                <thead>
                                    <tr>
                                        <th>Series</th>
                                        <th>Molecules</th>
                                        <th>Murcko scaffolds</th>
                                        <th>MCS status</th>
                                        <th>MCS atoms</th>
                                        <th>Median pIC50</th>
                                        <th>MCS (SMARTS)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.series.map(series => (
                                        <SeriesRow
                                            key={series.series_no}
                                            uniprot={uniprot}
                                            series={series}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>

                    )}

                    {data.series.length < data.matching && (

                        <button
                            className="mcs-button"
                            onClick={() => load(data.series.length, true)}
                            disabled={loading}
                        >
                            {loading
                                ? "Loading…"
                                : `Show more (${data.matching - data.series.length} left)`}
                        </button>

                    )}
                </>

            )}

        </div>
    );
}
