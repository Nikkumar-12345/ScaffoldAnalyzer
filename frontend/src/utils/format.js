// Formats a BLAST-style E-value the way sequence-search tools do:
// 0 for exact zero, scientific notation for very small values.
export function formatEvalue(value) {

    if (value === null || value === undefined) {
        return "-";
    }

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "-";
    }

    if (number === 0) {
        return "0.0";
    }

    if (number < 0.001 || number >= 1000) {
        return number.toExponential(1);
    }

    return number.toPrecision(2);
}
