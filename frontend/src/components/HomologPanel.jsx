import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { formatEvalue } from "../utils/format";


/*
 * Shows the proteins whose sequence is most similar to the target
 * that was analysed.
 *
 * The comparison is a Smith-Waterman local alignment (the same
 * alignment BLAST approximates) of the target against every protein
 * in the local ChEMBL database, precomputed so the lookup is instant.
 *
 * The cutoff for "counts as homologous" is adjustable. The slider is
 * limited to the range where sequence similarity can actually say
 * something: below the lower bound the alignment is in the twilight
 * zone, where similarity cannot establish homology on its own.
 */

const FALLBACK_BANDS = {
    similarity: { min: 40, max: 95, zones: [] },
    identity: { min: 20, max: 95, zones: [] }
};


function zoneFor(band, value) {

    return (band.zones || []).find(
        zone => value >= zone.from && value < zone.to
    );
}


export default function HomologPanel({ homologs, onFilterChange }) {

    const benchmark = useMemo(
        () => homologs?.benchmark || {},
        [homologs]
    );

    const bands = benchmark.bands || FALLBACK_BANDS;

    const [basis, setBasis] = useState(
        () => benchmark.basis || "similarity"
    );

    const [threshold, setThreshold] = useState(
        () => benchmark.threshold ?? 70
    );

    const [showBelow, setShowBelow] = useState(false);
    const [showAll, setShowAll] = useState(false);

    const navigate = useNavigate();

    const band = bands[basis] || FALLBACK_BANDS[basis];

    // Tell the dashboard, so the scaffold cards use the same cutoff
    useEffect(() => {

        onFilterChange?.({ basis, threshold });

    }, [basis, threshold, onFilterChange]);


    const rows = useMemo(
        () => homologs?.homologs || [],
        [homologs]
    );

    const valueOf = useMemo(
        () => hit => (basis === "identity"
            ? hit.identity
            : hit.similarity),
        [basis]
    );

    const passing = useMemo(
        () => rows.filter(hit => (valueOf(hit) ?? -1) >= threshold),
        [rows, valueOf, threshold]
    );

    if (!homologs) {
        return null;
    }

    // ----------------------------------------------
    // NOT AVAILABLE FOR THIS TARGET
    // ----------------------------------------------

    if (!homologs.available) {

        return (

            <div className="homolog-panel">

                <h2>Homologous Proteins</h2>

                <p className="homolog-intro">
                    Proteins whose sequence is similar to this target.
                    Closely related proteins often bind the same
                    molecules, so they show where a scaffold is likely
                    to lose selectivity.
                </p>

                <div className="homolog-empty">
                    {homologs.reason
                        || "No homology data is available."}
                </div>

            </div>

        );
    }

    const query = homologs.query || {};

    const listed = showBelow ? rows : passing;

    const visible = showAll ? listed : listed.slice(0, 10);

    const hidden = rows.length - passing.length;

    const zone = zoneFor(band, threshold);

    function changeBasis(next) {

        const nextBand = bands[next] || FALLBACK_BANDS[next];

        setBasis(next);

        setThreshold(current => Math.min(
            Math.max(current, nextBand.min),
            nextBand.max
        ));
    }

    function analyzeHomolog(uniprotId) {

        navigate(`/?uniprot=${encodeURIComponent(uniprotId)}`);
    }

    return (

        <div className="homolog-panel">

            <h2>Homologous Proteins</h2>

            <p className="homolog-intro">
                Proteins whose sequence is similar to{" "}
                <b>{query.target_name || query.uniprot_id}</b>.
                Closely related proteins often bind the same molecules,
                so they show where a scaffold is likely to lose
                selectivity.
            </p>


            {/* ========================================= */}
            {/* THRESHOLD CONTROL                         */}
            {/* ========================================= */}

            <div className="homolog-controls">

                <div className="control-row">

                    <span className="control-label">
                        Count as homologous at
                    </span>

                    <div className="basis-toggle">

                        {["similarity", "identity"].map(option => (

                            <button
                                key={option}
                                type="button"
                                className={
                                    "basis-option"
                                    + (basis === option
                                        ? " active"
                                        : "")
                                }
                                onClick={() => changeBasis(option)}
                            >
                                {option}
                            </button>

                        ))}

                    </div>

                </div>

                <div className="slider-row">

                    <span className="slider-bound">
                        {band.min}%
                    </span>

                    <input
                        type="range"
                        className="threshold-slider"
                        min={band.min}
                        max={band.max}
                        step={1}
                        value={threshold}
                        onChange={event =>
                            setThreshold(Number(event.target.value))
                        }
                        aria-label={
                            `Minimum ${basis} to count as homologous`
                        }
                    />

                    <span className="slider-bound">
                        {band.max}%
                    </span>

                    <span className="threshold-value">
                        {threshold}%
                    </span>

                </div>

                {zone && (

                    <p className="zone-note">
                        <span className="zone-label">
                            {zone.label}
                        </span>
                        {zone.note}
                    </p>

                )}

                {threshold !== benchmark.threshold && (

                    <button
                        type="button"
                        className="reset-threshold"
                        onClick={() => {
                            changeBasis(
                                benchmark.basis || "similarity"
                            );
                            setThreshold(benchmark.threshold ?? 70);
                        }}
                    >
                        Reset to the {benchmark.threshold}%{" "}
                        {benchmark.basis} benchmark
                    </button>

                )}

            </div>


            {/* ========================================= */}
            {/* HEADLINE NUMBERS                          */}
            {/* ========================================= */}

            <div className="homolog-stats">

                <div
                    className={
                        "homolog-stat"
                        + (passing.length > 0 ? " benchmark-pass" : "")
                    }
                >
                    <span className="homolog-stat-value">
                        {passing.length}
                    </span>
                    <span className="homolog-stat-label">
                        At or above {threshold}% {basis}
                    </span>
                </div>

                <div className="homolog-stat">
                    <span className="homolog-stat-value">
                        {passing.filter(
                            hit => hit.has_activity_data
                        ).length}
                    </span>
                    <span className="homolog-stat-label">
                        With activity data
                    </span>
                </div>

                <div className="homolog-stat">
                    <span className="homolog-stat-value">
                        {rows.length > 0
                            ? `${valueOf(rows[0])}%`
                            : "-"}
                    </span>
                    <span className="homolog-stat-label">
                        Closest {basis}
                    </span>
                </div>

                <div className="homolog-stat">
                    <span className="homolog-stat-value">
                        {query.length ? `${query.length} aa` : "-"}
                    </span>
                    <span className="homolog-stat-label">
                        Query length
                    </span>
                </div>

            </div>


            {rows.length === 0 && (

                <div className="homolog-empty">
                    No significant sequence homologs were found among
                    the proteins in the database.
                </div>

            )}


            {rows.length > 0 && passing.length === 0 && !showBelow && (

                <div className="homolog-empty">
                    No protein reaches {threshold}% {basis}. The closest
                    is <b>{valueOf(rows[0])}%</b> (
                    {rows[0].target_name || rows[0].uniprot_id}).
                    Lower the threshold to see the more distant
                    relatives.
                </div>

            )}


            {/* ========================================= */}
            {/* TABLE                                     */}
            {/* ========================================= */}

            {visible.length > 0 && (

                <div className="homolog-table-wrap">

                    <table className="homolog-table">

                        <thead>
                            <tr>
                                <th>Protein</th>
                                <th>UniProt</th>
                                <th>Organism</th>
                                <th className="num">Identity</th>
                                <th className="num">Similarity</th>
                                <th className="num">Coverage</th>
                                <th className="num">Bit score</th>
                                <th className="num">E-value</th>
                                <th>Activity data</th>
                            </tr>
                        </thead>

                        <tbody>

                            {visible.map(hit => {

                                const passes =
                                    (valueOf(hit) ?? -1) >= threshold;

                                return (

                                    <tr
                                        key={hit.uniprot_id}
                                        className={
                                            passes
                                                ? "benchmark-row"
                                                : "below-threshold"
                                        }
                                    >

                                        <td className="homolog-name">
                                            {hit.target_name
                                                || "Unknown protein"}
                                        </td>

                                        <td>
                                            <a
                                                href={
                                                    "https://www.uniprot"
                                                    + ".org/uniprotkb/"
                                                    + hit.uniprot_id
                                                }
                                                target="_blank"
                                                rel="noreferrer"
                                                className="homolog-link"
                                            >
                                                {hit.uniprot_id}
                                            </a>
                                        </td>

                                        <td className="homolog-organism">
                                            {hit.organism || "-"}
                                        </td>

                                        <td
                                            className={
                                                "num"
                                                + (basis === "identity"
                                                    ? " active-metric"
                                                    : "")
                                            }
                                        >
                                            <div className="identity-cell">
                                                <div className="identity-bar">
                                                    <div
                                                        className="identity-fill"
                                                        style={{
                                                            width:
                                                                `${Math.min(
                                                                    hit.identity,
                                                                    100
                                                                )}%`
                                                        }}
                                                    />
                                                </div>
                                                <span>
                                                    {hit.identity}%
                                                </span>
                                            </div>
                                        </td>

                                        <td
                                            className={
                                                "num"
                                                + (basis === "similarity"
                                                    ? " active-metric"
                                                    : "")
                                            }
                                        >
                                            {hit.similarity != null
                                                ? `${hit.similarity}%`
                                                : "-"}
                                            {passes && (
                                                <span
                                                    className="benchmark-tick"
                                                >
                                                    ✓
                                                </span>
                                            )}
                                        </td>

                                        <td className="num">
                                            {hit.coverage != null
                                                ? `${hit.coverage}%`
                                                : "-"}
                                        </td>

                                        <td className="num">
                                            {Math.round(hit.bit_score)}
                                        </td>

                                        <td className="num">
                                            {formatEvalue(hit.evalue)}
                                        </td>

                                        <td>
                                            {hit.has_activity_data ? (
                                                <button
                                                    type="button"
                                                    className="homolog-analyze"
                                                    onClick={() =>
                                                        analyzeHomolog(
                                                            hit.uniprot_id
                                                        )
                                                    }
                                                    title={
                                                        hit.molecule_count
                                                        + " molecules in"
                                                        + " the database"
                                                    }
                                                >
                                                    {hit.molecule_count}{" "}
                                                    molecules →
                                                </button>
                                            ) : (
                                                <span className="homolog-none">
                                                    none
                                                </span>
                                            )}
                                        </td>

                                    </tr>

                                );

                            })}

                        </tbody>

                    </table>

                </div>

            )}


            <div className="homolog-actions">

                {listed.length > 10 && (

                    <button
                        type="button"
                        className="homolog-toggle"
                        onClick={() => setShowAll(!showAll)}
                    >
                        {showAll
                            ? "Show top 10 only"
                            : `Show all ${listed.length}`}
                    </button>

                )}

                {hidden > 0 && (

                    <button
                        type="button"
                        className="homolog-toggle"
                        onClick={() => setShowBelow(!showBelow)}
                    >
                        {showBelow
                            ? `Hide the ${hidden} below ${threshold}%`
                            : `Show ${hidden} more below ${threshold}%`}
                    </button>

                )}

            </div>


            {homologs.method && (

                <p className="homolog-method">
                    Method: {homologs.method}
                </p>

            )}

        </div>

    );
}
