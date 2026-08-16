import axios from "axios";

const api = axios.create({
    baseURL: "https://scaffoldanalyzer-1.onrender.com",
    headers: {
        "Content-Type": "application/json"
    }
});

export default api;