import { Link } from "react-router-dom";

export default function Navbar() {
    return (
        <nav className="w-full bg-slate-900 border-b border-slate-700">

            <div className="max-w-7xl mx-auto flex justify-between items-center px-8 py-5">

                <h1 className="text-2xl font-bold text-cyan-400">
                    ScaffoldAnalyzer
                </h1>

                <div className="flex gap-8">

                    <Link to="/" className="hover:text-cyan-400">
                        Home
                    </Link>

                    <Link to="/dashboard" className="hover:text-cyan-400">
                        Dashboard
                    </Link>

                    <Link to="/scaffolds" className="hover:text-cyan-400">
                        Scaffolds
                    </Link>

                    <Link to="/about" className="hover:text-cyan-400">
                        About
                    </Link>

                </div>

            </div>

        </nav>
    );
}