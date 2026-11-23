import { useMemo, useState } from "react";

import api from "../services/api";
import { getAllScaffolds } from "../services/resultStore";


const PAGE = 50;

const SORTS = {
    rank: { label: "Rank", get: s => s.rank, dir: 1 },
    size: { label: "Molecules", get: s => s.occurrences, dir: -1 },
    mean: { label: "Mean pIC50", get: s => s.mean_pic50, dir: -1 },
    max: { label: "Max pIC50", get: s => s.max_pic50, dir: -1 },
    cliffs: {
        label: "Strong cliffs",
        get: s => s.side_chain_analysis?.strong_cliffs || 0,
        dir: -1
    }
};


function fixed(value, digits = 2) {

    return value === null || value === undefined || Number.isNaN(value)
        ? "-"
        : Number(value).toFixed(digits);
}


function Row({ scaffold, onOpen }) {

    const [open, setOpen] = useState(false);
    const [svg, setSvg] = useState(scaffold.svg || null);
    const [failed, setFailed] = useState(false);

    const analysis = scaffold.side_chain_analysis || {};
    const ranking = scaffold.ranking || {};

    async function toggle() {

        const next = !open;

        setOpen(next);

        if (!next || svg || failed) {
            return;
        }

        try {

            const response = await api.post("/scaffold/svg", {
                scaffold_smiles: scaffold.scaffold_smiles
            });

            setSvg(response.data.svg);

        } catch {

            setFailed(true);
        }
    }

    return (

        <>
            <tr className="mcs-row" onClick={toggle}>

                <td>{open ? "▾" : "▸"} #{scaffold.rank}</td>
                <td>{scaffold.occurrences}</td>
                <td>{fixed(scaffold.mean_pic50)}</td>
                <td>{fixed(scaffold.max_pic50)}</td>
                <td>{ranking.grade || "-"}</td>
                <td>{analysis.valid_one_atom_pairs || 0}</td>
                <td>{analysis.strong_cliffs || 0}</td>
                <td className="mcs-smarts" title={scaffold.scaffold_smiles}>
                    {scaffold.scaffold_smiles}
                </td>

            </tr>

            {open && (

                <tr className="mcs-detail">
                    <td colSpan={8}>

                        <div className="allsc-detail">

                            <div className="allsc-svg">
                                {svg
                                    ? <div dangerouslySetInnerHTML={{ __html: svg }} />
                                    : <span>{failed ? "Image unavailable" : "Drawing…"}</span>}
                            </div>

                            <div className="allsc-facts">
                                <p>
                                    {scaffold.occurrences} molecule(s),{" "}
                                    {scaffold.activity_records} activity record(s).
                                    pIC50 {fixed(scaffold.min_pic50)} to{" "}
                                    {fixed(scaffold.max_pic50)}, median{" "}
                                    {fixed(scaffold.median_pic50)}.
                                </p>
                                <p>
                                    Overall score {fixed(ranking.overall_score)}
                                    {ranking.label ? ` (${ranking.label})` : ""}.
                                </p>
                                <button
                                    className="mcs-button"
                                    onClick={() => onOpen(scaffold)}
                                >
                                    Investigate scaffold
                                </button>
                            </div>

                        </div>

                    </td>
                </tr>

            )}
        </>
    );
}


export default function AllScaffolds({ uniprot, total, onOpen }) {

    const all = getAllScaffolds(uniprot);

    const [query, setQuery] = useState("");
    const [sortKey, setSortKey] = useState("rank");
    const [multiOnly, setMultiOnly] = useState(false);
    const [withCliffs, setWithCliffs] = useState(false);
    const [shown, setShown] = useState(PAGE);

    const rows = useMemo(() => {

        if (!all) {
            return [];
        }

        const text = query.trim().toLowerCase();

        const sort = SORTS[sortKey];

        return all
            .filter(s => !multiOnly || s.occurrences > 1)
            .filter(s => !withCliffs
                || (s.side_chain_analysis?.strong_cliffs || 0) > 0)
            .filter(s => !text
                || s.scaffold_smiles.toLowerCase().includes(text)
                || `scf-${s.id}`.includes(text)
                || (s.molecules || []).some(
                    m => m.chembl_id.toLowerCase() === text
                ))
            .sort((a, b) => {

                const x = sort.get(a) ?? -Infinity;
                const y = sort.get(b) ?? -Infinity;

                return (x - y) * sort.dir || a.rank - b.rank;
            });

    }, [all, query, sortKey, multiOnly, withCliffs]);

    if (!all) {

        return (
            <div className="homolog-empty">
                The full list of {total?.toLocaleString("en-US")} scaffolds is
                kept only for the session that ran the analysis. Run the
                analysis again from the home page to browse all of them.
            </div>
        );
    }

    return (

        <>
            <div className="mcs-toolbar allsc-toolbar">

                <input
                    className="text-input allsc-search"
                    type="search"
                    placeholder="Search scaffold SMILES, SCF id or ChEMBL molecule id"
                    value={query}
                    onChange={e => {
                        setQuery(e.target.value);
                        setShown(PAGE);
                    }}
                />

                <label>
                    Sort by{" "}
                    <select
                        value={sortKey}
                        onChange={e => setSortKey(e.target.value)}
                    >
                        {Object.entries(SORTS).map(([key, sort]) => (
                            <option key={key} value={key}>{sort.label}</option>
                        ))}
                    </select>
                </label>

                <label>
                    <input
                        type="checkbox"
                        checked={multiOnly}
                        onChange={e => {
                            setMultiOnly(e.target.checked);
                            setShown(PAGE);
                        }}
                    />
                    {" "}2+ molecules
                </label>

                <label>
                    <input
                        type="checkbox"
                        checked={withCliffs}
                        onChange={e => {
                            setWithCliffs(e.target.checked);
                            setShown(PAGE);
                        }}
                    />
                    {" "}Has strong cliffs
                </label>

            </div>

            <p className="homolog-intro">
                {rows.length.toLocaleString("en-US")} of{" "}
                {all.length.toLocaleString("en-US")} scaffolds. Open a row for
                its drawing and a link to the full analysis.
            </p>

            {rows.length === 0 ? (

                <div className="homolog-empty">No scaffolds match.</div>

            ) : (

                <div className="homolog-table-wrap allsc-wrap">
                    <table className="homolog-table mcs-table">
                        <thead>
                            <tr>
                                <th>Rank</th>
                                <th>Molecules</th>
                                <th>Mean pIC50</th>
                                <th>Max pIC50</th>
                                <th>Grade</th>
                                <th>One-atom pairs</th>
                                <th>Strong cliffs</th>
                                <th>Scaffold SMILES</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.slice(0, shown).map(scaffold => (
                                <Row
                                    key={scaffold.id}
                                    scaffold={scaffold}
                                    onOpen={onOpen}
                                />
                            ))}
                        </tbody>
                    </table>
                </div>

            )}

            {shown < rows.length && (

                <button
                    className="mcs-button"
                    onClick={() => setShown(shown + PAGE)}
                >
                    Show more ({rows.length - shown} left)
                </button>

            )}
        </>
    );
}
