import { NavLink, Link } from "react-router-dom";

const LINKS = [
    { to: "/", label: "Analyze", end: true },
    { to: "/methods", label: "Methods" },
    { to: "/about", label: "About" }
];

export default function Navbar() {

    return (

        <header className="site-nav">

            <div className="site-nav-inner">

                <Link to="/" className="site-brand">
                    <span className="site-brand-mark" aria-hidden="true">
                        <svg viewBox="0 0 24 24" width="22" height="22">
                            <polygon
                                points="12,2.5 20,7 20,17 12,21.5 4,17 4,7"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="1.6"
                            />
                            <polygon
                                points="12,7.5 16,9.8 16,14.4 12,16.7 8,14.4 8,9.8"
                                fill="currentColor"
                            />
                        </svg>
                    </span>
                    ScaffoldAnalyzer
                </Link>

                <nav className="site-links" aria-label="Main">

                    {LINKS.map(link => (
                        <NavLink
                            key={link.to}
                            to={link.to}
                            end={link.end}
                            className={({ isActive }) =>
                                "site-link" + (isActive ? " active" : "")
                            }
                        >
                            {link.label}
                        </NavLink>
                    ))}

                    <a
                        className="site-link"
                        href="https://github.com/Nikkumar-12345/ScaffoldAnalyzer"
                        target="_blank"
                        rel="noreferrer"
                    >
                        GitHub ↗
                    </a>

                </nav>

            </div>

        </header>
    );
}
