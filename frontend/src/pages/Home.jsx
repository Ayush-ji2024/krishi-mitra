import { useLang } from "../i18n/LangContext";
import { CROPS, names, SOILS } from "../data";
import {
  IconArrowRight, IconCamera, IconFlask, IconPin, IconRain, IconShield, IconSprout,
} from "../components/Icons";

const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });

// A static, decorative "phone" showing what a result looks like.
function PreviewCard() {
  const { t, lang } = useLang();
  // The real answer our model gave for a Begusarai rice field (rice 95%, jute 5%).
  const rows = [
    { crop: "rice", level: 3, cls: "good", match: "res.strong" },
    { crop: "jute", level: 1, cls: "low", match: "res.weak" },
  ];
  return (
    <div className="preview" aria-hidden="true">
      <div className="preview-top">
        <span className="preview-dot" /><span className="preview-dot" /><span className="preview-dot" />
      </div>
      <p className="preview-title">{t("res.title")}</p>
      <p className="preview-place"><IconPin width={14} height={14} /> {t("home.preview.place")}</p>
      {rows.map((r, i) => {
        const n = names(CROPS[r.crop], lang);
        return (
          <div className={`preview-row ${i === 0 ? "is-top" : ""}`} key={r.crop}>
            <span className="preview-emoji">{CROPS[r.crop].emoji}</span>
            <span className="preview-text">
              <b>{n.main}</b>
              <span className="meter small">
                {[1, 2, 3].map((k) => <span key={k} className={k <= r.level ? `on ${r.cls}` : ""} />)}
                <span className="meter-label">{t(r.match)}</span>
              </span>
            </span>
            {i === 0 && <span className="ribbon">{t("res.best")}</span>}
          </div>
        );
      })}
    </div>
  );
}

export default function Home() {
  const { t, lang } = useLang();

  const steps = [
    { icon: <IconCamera />, title: t("home.how.1.t"), text: t("home.how.1.d") },
    { icon: <IconPin />, title: t("home.how.2.t"), text: t("home.how.2.d") },
    { icon: <IconFlask />, title: t("home.how.3.t"), text: t("home.how.3.d") },
  ];
  const features = [
    { icon: <IconCamera />, title: t("home.feat.1.t"), text: t("home.feat.1.d") },
    { icon: <IconRain />, title: t("home.feat.2.t"), text: t("home.feat.2.d") },
    { icon: <IconSprout />, title: t("home.feat.3.t"), text: t("home.feat.3.d") },
    { icon: <IconShield />, title: t("home.feat.4.t"), text: t("home.feat.4.d") },
  ];
  const faqs = [1, 2, 3].map((i) => ({ q: t(`home.faq.${i}.q`), a: t(`home.faq.${i}.a`) }));

  return (
    <>
      {/* ---------- Hero ---------- */}
      <section className="home-hero">
        <div className="home-hero-inner">
          <div className="hero-copy">
            <p className="eyebrow">{t("home.eyebrow")}</p>
            <h1>
              {t("home.title1")} <span className="accent">{t("home.title2")}</span>
            </h1>
            <p className="tagline">{t("home.tagline")}</p>
            <div className="hero-ctas">
              <a href="#/advisor" className="btn btn-gold">{t("home.cta")} <IconArrowRight /></a>
              <button type="button" className="btn btn-ghost" onClick={() => scrollTo("how")}>{t("home.ctaHow")}</button>
            </div>
          </div>
          <PreviewCard />
        </div>

        <dl className="stats">
          <div><dt>22</dt><dd>{t("home.stat.crops")}</dd></div>
          <div><dt>4</dt><dd>{t("home.stat.soils")}</dd></div>
          <div><dt>2</dt><dd>{t("home.stat.lang")}</dd></div>
          <div><dt>₹0</dt><dd>{t("home.stat.free")}</dd></div>
        </dl>
      </section>

      {/* ---------- How it works ---------- */}
      <section className="section" id="how">
        <div className="container">
          <h2 className="section-title">{t("home.how.title")}</h2>
          <p className="section-sub">{t("home.how.sub")}</p>
          <ol className="how-grid">
            {steps.map((s, i) => (
              <li key={i} className="how-card">
                <span className="how-num">{i + 1}</span>
                <span className="how-icon">{s.icon}</span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------- Features ---------- */}
      <section className="section section-tinted">
        <div className="container">
          <h2 className="section-title">{t("home.feat.title")}</h2>
          <div className="feature-grid">
            {features.map((f, i) => (
              <div key={i} className="feature">
                <span className="feature-icon">{f.icon}</span>
                <div>
                  <h3>{f.title}</h3>
                  <p>{f.text}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="soil-strip">
            {Object.entries(SOILS).map(([key, s]) => {
              const n = names(s, lang);
              return (
                <div key={key} className="soil-chip">
                  <span className="swatch" style={{ background: s.color }} />
                  <span><b>{n.main}</b> <small>{n.sub}</small></span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ---------- Crops ---------- */}
      <section className="section">
        <div className="container">
          <h2 className="section-title">{t("home.crops.title")}</h2>
          <p className="section-sub">{t("home.crops.missing")}</p>
          <ul className="crop-cloud">
            {Object.entries(CROPS).map(([key, c]) => {
              const n = names(c, lang);
              return (
                <li key={key}>
                  <span aria-hidden="true">{c.emoji}</span> {n.main} <small>{n.sub}</small>
                </li>
              );
            })}
          </ul>
        </div>
      </section>

      {/* ---------- FAQ ---------- */}
      <section className="section section-tinted">
        <div className="container narrow">
          <h2 className="section-title">{t("home.faq.title")}</h2>
          <div className="faq">
            {faqs.map((f, i) => (
              <details key={i} open={i === 0}>
                <summary>{f.q}</summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ---------- Final call to action ---------- */}
      <section className="final-cta">
        <div className="container">
          <h2>{t("home.final.title")}</h2>
          <p>{t("home.final.text")}</p>
          <a href="#/advisor" className="btn btn-gold">{t("home.cta")} <IconArrowRight /></a>
        </div>
      </section>
    </>
  );
}
