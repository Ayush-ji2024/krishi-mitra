import { useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n/useLang";
import { ALL_FIELDS, TEST_FIELDS, WEATHER_FIELDS } from "../advisor/useAdvisor";
import Stepper from "../advisor/Stepper";
import SoilStep from "../advisor/SoilStep";
import WeatherStep from "../advisor/WeatherStep";
import SoilTestStep from "../advisor/SoilTestStep";
import ResultsStep from "../advisor/ResultsStep";
import { IconArrowLeft, IconArrowRight, IconSprout } from "../components/Icons";

// The advisor as a 4-step wizard: one question per screen is much easier on a
// phone than one long form, and the stepper shows how far along you are.
export default function Advisor({ advisor, meta, serverError }) {
  const { t } = useLang();
  const a = advisor;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const steps = [
    { key: "step.soil", done: !!a.soilType },
    { key: "step.weather", done: a.filled(WEATHER_FIELDS) },
    { key: "step.test", done: a.filled(TEST_FIELDS) },
    { key: "step.results", done: !!a.result },
  ];
  const label = (f) => (WEATHER_FIELDS.includes(f) ? t(`weather.${f}`) : t(`test.${f}`));
  const missingIn = (fields) => fields.filter((f) => a.values[f] === "");

  function go(i) {
    setError("");
    a.setStep(i);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function next() {
    if (a.step === 1) {
      const missing = missingIn(WEATHER_FIELDS);
      if (missing.length) return setError(t("form.missing", { fields: missing.map(label).join(", ") }));
    }
    go(a.step + 1);
  }

  async function getResults() {
    const missing = missingIn(ALL_FIELDS);
    if (missing.length) {
      const msg = t("form.missing", { fields: missing.map(label).join(", ") });
      if (missingIn(WEATHER_FIELDS).length) go(1); // weather is on another screen - take them there
      return setError(msg);
    }
    const body = Object.fromEntries(ALL_FIELDS.map((f) => [f, Number(a.values[f])]));
    if (a.soilType) body.soil_type = a.soilType;

    setError("");
    setLoading(true);
    try {
      a.setResult(await api.recommend(body));
      go(3);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="advisor">
      <div className="advisor-head">
        <div className="container">
          <p className="advisor-kicker"><IconSprout width={16} height={16} /> {t("adv.title")}</p>
          <Stepper
            steps={steps}
            current={a.step}
            canOpen={(i) => i < 3 || !!a.result}
            onOpen={go}
          />
        </div>
      </div>

      <div className="container advisor-body">
        {serverError && <div className="notice error">{serverError}</div>}

        <div className="wizard-card" key={a.step /* re-mount = small fade-in on every step */}>
          <p className="step-count">{t("form.stepOf", { n: a.step + 1, total: 4 })}</p>
          {a.step === 0 && <SoilStep advisor={a} soilTypes={meta?.soil_types ?? []} />}
          {a.step === 1 && <WeatherStep advisor={a} />}
          {a.step === 2 && <SoilTestStep advisor={a} ranges={meta?.feature_ranges} />}
          {a.step === 3 && <ResultsStep advisor={a} onEdit={() => go(0)} />}

          {error && <div className="notice error">{error}</div>}
        </div>

        {a.step < 3 && (
          <div className="wizard-actions">
            {a.step > 0 ? (
              <button type="button" className="btn btn-plain" onClick={() => go(a.step - 1)}>
                <IconArrowLeft width={18} height={18} /> {t("btn.back")}
              </button>
            ) : <span />}

            {a.step < 2 && (
              <button type="button" className="btn btn-primary" onClick={next}>
                {a.step === 0 && !a.soilType ? t("btn.skip") : t("btn.next")} <IconArrowRight width={18} height={18} />
              </button>
            )}
            {a.step === 2 && (
              <button type="button" className="btn btn-primary" onClick={getResults} disabled={loading || !meta}>
                {loading ? <><span className="spinner" /> {t("res.loading")}</> : <><IconSprout width={18} height={18} /> {t("btn.get")}</>}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
