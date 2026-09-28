import { useLang } from "../i18n/LangContext";
import { IconGithub } from "./Icons";

export const GITHUB_URL = "https://github.com/Ayush-ji2024/krishi-mitra";

export default function Footer() {
  const { t } = useLang();
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div>
          <a href="#/" className="brand brand-footer"><span aria-hidden="true">🌾</span> Krishi Mitra</a>
          <p>{t("footer.made")}</p>
        </div>
        <nav className="footer-links" aria-label="Footer">
          <a href="#/advisor">{t("nav.advisor")}</a>
          <a href="#/about">{t("nav.about")}</a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer"><IconGithub width={16} height={16} /> {t("footer.source")}</a>
        </nav>
      </div>
      <p className="footer-credits">{t("footer.credits")}</p>
    </footer>
  );
}
