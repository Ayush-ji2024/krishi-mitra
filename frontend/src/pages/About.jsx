import { useLang } from "../i18n/LangContext";
import { IconAlert, IconArrowRight, IconCamera, IconCheck, IconFlask, IconPin, IconSprout } from "../components/Icons";

// Written for farmers, in plain words. Technical details (models, metrics,
// tech stack) live in the project's README on GitHub, not here.
export default function About() {
  const { t } = useLang();

  const how = [
    { icon: <IconCamera />, text: t("about.how.soil") },
    { icon: <IconFlask />, text: t("about.how.crop") },
    { icon: <IconSprout />, text: t("about.how.fao") },
    { icon: <IconPin />, text: t("about.how.weather") },
  ];

  return (
    <div className="about">
      <section className="page-hero">
        <div className="container narrow">
          <h1>{t("about.title")}</h1>
          <p>{t("about.intro")}</p>
        </div>
      </section>

      <div className="container narrow about-body">
        <section className="about-block">
          <h2>{t("about.how.title")}</h2>
          <ul className="how-list">
            {how.map((h, i) => (
              <li key={i}><span className="how-list-icon">{h.icon}</span><span>{h.text}</span></li>
            ))}
          </ul>
        </section>

        <section className="about-block">
          <h2>{t("about.acc.title")}</h2>
          <ul className="check-list">
            {[1, 2, 3].map((i) => (
              <li key={i}><span className="check"><IconCheck width={14} height={14} /></span>{t(`about.acc.${i}`)}</li>
            ))}
          </ul>
        </section>

        <section className="about-block">
          <h2>{t("about.limits.title")}</h2>
          <ul className="check-list warn">
            {[1, 2, 3].map((i) => (
              <li key={i}><span className="check"><IconAlert width={14} height={14} /></span>{t(`about.limits.${i}`)}</li>
            ))}
          </ul>
        </section>

        <section className="about-block">
          <h2>{t("about.sources.title")}</h2>
          <ul className="plain-list">
            {[1, 2, 3].map((i) => <li key={i}>{t(`about.sources.${i}`)}</li>)}
          </ul>
          <p className="muted about-team">{t("about.team")}</p>
        </section>

        <div className="about-ctas">
          <a href="#/advisor" className="btn btn-primary">{t("home.cta")} <IconArrowRight width={18} height={18} /></a>
        </div>
      </div>
    </div>
  );
}
