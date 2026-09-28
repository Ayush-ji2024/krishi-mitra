import { useEffect, useState } from "react";
import { api } from "./api";
import { useHashRoute } from "./hooks/useHashRoute";
import { useAdvisor } from "./advisor/useAdvisor";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import Home from "./pages/Home";
import Advisor from "./pages/Advisor";
import About from "./pages/About";
import "./styles/base.css";
import "./styles/home.css";
import "./styles/advisor.css";
import "./styles/about.css";

export default function App() {
  const path = useHashRoute();
  const advisor = useAdvisor();                   // kept here so it survives page changes
  const [meta, setMeta] = useState(null);         // soil types, crops, ranges from the backend
  const [serverError, setServerError] = useState("");

  // Load /meta once, when the site opens.
  useEffect(() => {
    api.meta().then(setMeta).catch((err) => setServerError(err.message));
  }, []);

  let page;
  if (path.startsWith("/advisor")) page = <Advisor advisor={advisor} meta={meta} serverError={serverError} />;
  else if (path.startsWith("/about")) page = <About />;
  else page = <Home />;

  return (
    <div className="site">
      {/* Not a plain href="#main": with hash routing that would change the page. */}
      <button type="button" className="skip-link" onClick={() => document.getElementById("main")?.focus()}>
        Skip to content
      </button>
      <Navbar path={path} />
      <main id="main" tabIndex={-1}>{page}</main>
      <Footer />
    </div>
  );
}
