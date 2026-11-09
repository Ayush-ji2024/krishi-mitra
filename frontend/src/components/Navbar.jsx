import { useState } from "react";
import { useLang } from "../i18n/useLang";
import { IconClose, IconMenu } from "./Icons";

const LINKS = [
  { href: "#/", key: "nav.home", match: (p) => p === "/" },
  { href: "#/advisor", key: "nav.advisor", match: (p) => p.startsWith("/advisor") },
  { href: "#/about", key: "nav.about", match: (p) => p.startsWith("/about") },
];

export default function Navbar({ path }) {
  const { t, lang, setLang } = useLang();
  // The menu remembers which page it was opened on, so it is closed
  // automatically when the page changes (no effect + setState needed).
  const [openOn, setOpenOn] = useState(null);
  const open = openOn === path;

  return (
    <header className="navbar">
      <div className="nav-inner">
        <a href="#/" className="brand">
          <span className="brand-mark" aria-hidden="true">🌾</span>
          <span>Krishi Mitra</span>
        </a>

        <nav className="nav-links" aria-label="Main">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className={l.match(path) ? "active" : ""}>{t(l.key)}</a>
          ))}
        </nav>

        <div className="nav-actions">
          <button
            type="button"
            className="lang-btn"
            onClick={() => setLang(lang === "en" ? "hi" : "en")}
            aria-label={t("nav.switchLabel")}
          >
            {t("nav.switch")}
          </button>
          <button
            type="button"
            className="menu-btn"
            aria-label={t("nav.menu")}
            aria-expanded={open}
            onClick={() => setOpenOn(open ? null : path)}
          >
            {open ? <IconClose /> : <IconMenu />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="mobile-menu" aria-label="Mobile">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className={l.match(path) ? "active" : ""}>{t(l.key)}</a>
          ))}
        </nav>
      )}
    </header>
  );
}
