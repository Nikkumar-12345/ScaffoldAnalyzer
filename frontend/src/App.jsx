import {
    BrowserRouter,
    Routes,
    Route
} from "react-router-dom";

import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import ScaffoldDetails from "./pages/ScaffoldDetails";

export default function App() {

    return (

        <BrowserRouter>

            <Routes>

                <Route
                    path="/"
                    element={<Home />}
                />

                <Route
                    path="/dashboard"
                    element={<Dashboard />}
                />

                <Route
                    path="/scaffold"
                    element={<ScaffoldDetails />}
                />

            </Routes>

        </BrowserRouter>

    );

}