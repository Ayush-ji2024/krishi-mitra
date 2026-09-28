import { useLang } from "../i18n/LangContext";
import { cropInfo, names, SOILS } from "../data";
import { IconAlert, IconPin, IconRefresh } from "../components/Icons";

// Step 4: the recommendations, in plain words.
// NOTE: "score" is only used for ORDER. We never show it as a percentage,
// because "0.7" would be misread as "70% chance" (it is probability x soil weight).
function matchInfo(p) {
  if (p >= 0.7) return { key: "res.strong", level: 3, cls: "good" };
  if (p >= 0.3) return { key: "res.possible", level: 2, cls: "mid" };
  return { key: "res.weak", level: 1, cls: "low" };
}
const SOIL_CLS = { good: "good", possible: "mid", poor: "low" };

export default function ResultsStep({ advisor, onEdit }) {
  const { t, lang } = useLang();
  const { result, soilType, values, place, reset } = advisor;
  if (!result) return null;

  const allWeak = result.recommendations.every((r) => r.probability < 0.3);
  const soilName = soilType ? names(SOILS[soilType], lang).main : t("res.notGiven");

  return (
    <div className="step-panel">
      <h1 className="step-title">{t("res.title")}</h1>

      {/* What the suggestion is based on - so the farmer can spot a typo. */}
      <div className="input-summary" aria-label={t("res.inputs")}>
        <span className="chip">{t("res.soilLabel")}: <b>{soilName}</b></span>
        {place && <span className="chip"><IconPin width={13} height={13} /> <b>{place.place.name}</b></span>}
        <span className="chip">🌡 <b>{values.temperature}°C</b></span>
        <span className="chip">💧 <b>{values.humidity}%</b></span>
        <span className="chip">🌧 <b>{values.rainfall} mm</b></span>
        <span className="chip">N-P-K <b>{values.N}-{values.P}-{values.K}</b></span>
        <span className="chip">pH <b>{values.ph}</b></span>
      </div>

      {!soilType && <p className="muted small">{t("res.noSoil")}</p>}
      {allWeak && <div className="notice warn">{t("res.allWeak")}</div>}

      <ol className="crop-list">
        {result.recommendations.map((r, i) => {
          const crop = cropInfo(r.crop);
          const n = names(crop, lang);
          const match = matchInfo(r.probability);
          return (
            <li key={r.crop} className={`crop-card ${i === 0 ? "is-top" : ""}`}>
              {i === 0 && <span className="ribbon">{t("res.best")}</span>}
              <span className="crop-emoji" aria-hidden="true">{crop.emoji}</span>
              <div className="crop-main">
                <div className="crop-name">{n.main} {n.sub && <span className="sub">{n.sub}</span>}</div>
                <div className="meter">
                  {[1, 2, 3].map((k) => <span key={k} className={k <= match.level ? `on ${match.cls}` : ""} />)}
                  <span className="meter-label">{t(match.key)}</span>
                </div>
                {r.soil_suitability && (
                  <span className={`pill ${SOIL_CLS[r.soil_suitability]}`}>{t(`res.soil.${r.soil_suitability}`)}</span>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {result.warnings.length > 0 && (
        <div className="notice warn">
          <IconAlert width={16} height={16} /> <b>{t("res.note")}</b>
          <ul>{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <p className="disclaimer">{t("res.disclaimer")}</p>

      <div className="result-actions">
        <button type="button" className="btn btn-outline" onClick={onEdit}>{t("btn.edit")}</button>
        <button type="button" className="btn btn-plain" onClick={reset}><IconRefresh width={18} height={18} /> {t("btn.restart")}</button>
      </div>
    </div>
  );
}
