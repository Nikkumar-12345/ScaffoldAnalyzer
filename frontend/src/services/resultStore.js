/*
 * Keeps the full scaffold list of the latest analysis in memory.
 *
 * It is large (several MB), so it is deliberately not placed in the
 * router's history state, which browsers limit. If the page is reloaded
 * the store is empty and the "all scaffolds" table asks the user to
 * re-run the analysis; everything else keeps working from history state.
 */

let allScaffolds = null;
let owner = null;

export function setAllScaffolds(uniprot, scaffolds) {
    owner = uniprot || null;
    allScaffolds = Array.isArray(scaffolds) ? scaffolds : null;
}

export function getAllScaffolds(uniprot) {
    return owner === (uniprot || null) ? allScaffolds : null;
}
