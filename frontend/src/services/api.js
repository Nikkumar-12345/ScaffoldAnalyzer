import axios from "axios";

// Backend URL. Override with VITE_API_URL (for example in a local
// .env file: VITE_API_URL=http://localhost:8000) to use a local backend.
export const API_BASE_URL =
    import.meta.env.VITE_API_URL ||
    "https://scaffold-analyzer-backend-v11.onrender.com";

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        "Content-Type": "application/json"
    }
});


// Turns any request error into a readable message.
export function getErrorMessage(err, fallback = "Something went wrong.") {

    if (err?.response) {

        const detail = err.response.data?.detail;

        if (typeof detail === "string" && detail) {
            return detail;
        }

        if (detail) {
            return JSON.stringify(detail, null, 2);
        }

        return `${fallback} (server returned status ${err.response.status})`;
    }

    if (err?.request) {
        return (
            "Could not reach the analysis server. It may be starting up " +
            "or temporarily unavailable - please try again in a minute."
        );
    }

    return err?.message || fallback;
}


const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));


/*
 * Runs a target analysis as a background job and reports progress.
 *
 * onProgress receives { progress (0-100), stage, status, elapsed }.
 * Resolves with the analysis result; rejects with an Error whose
 * message is user-facing.
 *
 * Falls back to the original single-request endpoint if the server
 * does not support jobs yet (e.g. an older backend is deployed).
 */
export async function runAnalysis(uniprotId, onProgress, signal) {

    let job;

    try {

        const response = await api.post(
            "/analyze/start",
            { uniprot_id: uniprotId },
            { signal }
        );

        job = response.data;

    } catch (err) {

        const status = err?.response?.status;

        if (status === 404 || status === 405) {

            onProgress?.({
                progress: null,
                stage: "Analyzing target...",
                status: "running"
            });

            const response = await api.post(
                "/analyze/",
                { uniprot_id: uniprotId },
                { signal }
            ).catch((error) => {
                throw new Error(
                    getErrorMessage(error, "Analysis failed."),
                    { cause: error }
                );
            });

            return response.data;
        }

        throw new Error(
            getErrorMessage(err, "Could not start the analysis."),
            { cause: err }
        );
    }

    let failures = 0;

    while (true) {

        if (signal?.aborted) {
            throw new DOMException("Aborted", "AbortError");
        }

        onProgress?.(job);

        if (job.status === "error") {
            throw new Error(
                job.error?.message || "The analysis failed."
            );
        }

        if (job.status === "done") {
            break;
        }

        await sleep(1000);

        try {

            const response = await api.get(
                `/analyze/status/${job.job_id}`,
                { signal }
            );

            job = response.data;
            failures = 0;

        } catch (err) {

            if (err?.response?.status === 404) {
                throw new Error(getErrorMessage(err), { cause: err });
            }

            // Brief network hiccup: keep polling for a while
            failures += 1;

            if (failures > 30) {
                throw new Error(getErrorMessage(err), { cause: err });
            }
        }
    }

    onProgress?.({
        ...job,
        progress: 100,
        stage: "Loading results"
    });

    try {

        const response = await api.get(
            `/analyze/result/${job.job_id}`,
            { signal }
        );

        return response.data;

    } catch (err) {

        throw new Error(
            getErrorMessage(err, "Could not load the results."),
            { cause: err }
        );
    }
}

export default api;
