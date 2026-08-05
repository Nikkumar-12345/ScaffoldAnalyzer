import { useState } from "react";
import { useNavigate } from "react-router-dom";

import Navbar from "../components/Navbar";
import api from "../services/api";

export default function Home() {

    const [uniprot, setUniprot] = useState("");
    const [loading, setLoading] = useState(false);

    const navigate = useNavigate();

    async function analyzeTarget() {

        if (uniprot.trim() === "") {
            alert("Please enter a UniProt ID");
            return;
        }

        try {

            setLoading(true);

            const response = await api.post("/analyze/", {
                uniprot_id: uniprot
            });

            console.log("SUCCESS");
            console.log(response.data);

            navigate("/dashboard", {
                state: {
                    result: response.data
                }
            });

        }
        catch (err) {

            console.log("===== ERROR =====");

            console.log(err);

            if (err.response) {

                console.log("Status:", err.response.status);

                console.log("Data:", err.response.data);

                alert(
                    "Backend Error\n\n" +
                    JSON.stringify(err.response.data, null, 2)
                );

            }
            else if (err.request) {

                console.log(err.request);

                alert(
                    "Cannot connect to backend.\n\n" +
                    "Make sure FastAPI is running on port 8000."
                );

            }
            else {

                console.log(err.message);

                alert(err.message);

            }

        }
        finally {

            setLoading(false);

        }

    }

    return (

        <>

            <Navbar />

            <div
                style={{
                    padding: "60px",
                    color: "white"
                }}
            >

                <h1>Scaffold Analyzer</h1>

                <br />

                <input
                    type="text"
                    value={uniprot}
                    onChange={(e) => setUniprot(e.target.value)}
                    placeholder="Enter UniProt ID (Example: P00533)"
                    style={{
                        width: "350px",
                        padding: "12px",
                        fontSize: "18px"
                    }}
                />

                <br /><br />

                <button
                    onClick={analyzeTarget}
                    disabled={loading}
                    style={{
                        width: "180px",
                        padding: "12px",
                        fontSize: "16px",
                        cursor: "pointer"
                    }}
                >
                    {loading ? "Analyzing..." : "Analyze"}
                </button>

            </div>

        </>

    );

}