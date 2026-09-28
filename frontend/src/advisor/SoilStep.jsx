import { useState } from "react";
import { api } from "../api";
import { names, SOILS } from "../data";
import { useLang } from "../i18n/LangContext";
import { IconCamera } from "../components/Icons";

const MAX_BYTES = 5 * 1024 * 1024; // same limit as the backend

// Step 1: the soil type - from a photo (soil model) or picked by hand.
export default function SoilStep({ advisor, soilTypes }) {
  const { t, lang } = useLang();
  const { soilType, setSoilType, photo, setPhoto } = advisor;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  async function analyse(file) {
    if (!file) return;
    setError("");
    // Check on the client first: faster feedback, and no wasted upload.
    if (!file.type.startsWith("image/")) return setError(t("soil.notImage"));
    if (file.size > MAX_BYTES) return setError(t("soil.tooBig"));

    if (photo?.url) URL.revokeObjectURL(photo.url); // free the old preview
    const url = URL.createObjectURL(file);
    setPhoto({ url, prediction: null });
    setLoading(true);
    try {
      const prediction = await api.predictSoil(file);
      setPhoto({ url, prediction });
      setSoilType(prediction.soil_type); // pre-select; the user can still change it
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const prediction = photo?.prediction;
  const soils = soilTypes.length ? soilTypes : Object.keys(SOILS);
  const soilName = (key) => (SOILS[key] ? names(SOILS[key], lang).main : key);

  return (
    <div className="step-panel">
      <h1 className="step-title">{t("soil.title")}</h1>
      <p className="step-sub">{t("soil.sub")}</p>

      <div className="soil-layout">
        <label
          className={`dropzone ${dragging ? "is-dragging" : ""} ${photo ? "has-image" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); analyse(e.dataTransfer.files?.[0]); }}
        >
          {photo ? (
            <>
              <img src={photo.url} alt="" />
              {!loading && <span className="dropzone-change">{t("soil.change")}</span>}
            </>
          ) : (
            <span className="dropzone-text">
              <span className="dropzone-icon"><IconCamera width={26} height={26} /></span>
              <b>{t("soil.add")}</b>
              <small>{t("soil.addHint")}</small>
            </span>
          )}
          {loading && <span className="dropzone-overlay"><span className="spinner" /> {t("soil.analysing")}</span>}
          {/* accept="image/*" lets phones offer both "Camera" and "Gallery". */}
          <input type="file" accept="image/*" onChange={(e) => analyse(e.target.files?.[0])} hidden />
        </label>

        <div className="soil-result">
          {prediction ? (
            <div className={`detect ${prediction.low_confidence ? "is-unsure" : ""}`}>
              <p className="detect-title">{t("soil.looks", { soil: soilName(prediction.soil_type) })}</p>
              {/* One bar per soil type: how sure the model is, and what the runner-up was. */}
              <div className="prob-bars">
                {Object.entries(prediction.probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .map(([key, p]) => (
                    <div className="prob-row" key={key}>
                      <span>{soilName(key)}</span>
                      <span className="prob-track">
                        <span style={{ width: `${Math.round(p * 100)}%`, background: SOILS[key]?.color }} />
                      </span>
                      <span className="prob-val">{Math.round(p * 100)}%</span>
                    </div>
                  ))}
              </div>
              {prediction.low_confidence && <p className="detect-warn">{t("soil.unsure")}</p>}
            </div>
          ) : (
            !error && <p className="muted">{t("soil.optional")}</p>
          )}
          {error && <div className="notice error">{error}</div>}
        </div>
      </div>

      <p className="label-strong">{t("soil.or")}</p>
      <div className="soil-picker" role="radiogroup" aria-label={t("step.soil")}>
        {soils.map((key) => {
          const s = SOILS[key] ?? { en: key, hi: "", color: "#999", note: { en: "", hi: "" } };
          const n = names(s, lang);
          const selected = soilType === key;
          return (
            <button
              type="button"
              key={key}
              role="radio"
              aria-checked={selected}
              className={`soil-option ${selected ? "is-selected" : ""}`}
              onClick={() => setSoilType(selected ? "" : key)}
            >
              <span className="swatch" style={{ background: s.color }} />
              <span className="soil-name">{n.main} <span className="sub">{n.sub}</span></span>
              <small>{s.note[lang] ?? s.note.en}</small>
            </button>
          );
        })}
      </div>
    </div>
  );
}
