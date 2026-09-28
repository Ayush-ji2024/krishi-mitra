import { useEffect, useState } from "react";
import { api } from "../api";
import { SOILS } from "../data";
import StepCard from "./StepCard";
import { IconCamera } from "./Icons";

const MAX_BYTES = 5 * 1024 * 1024; // same limit as the backend

// Step 1: the soil type - from a photo (soil model) or picked by hand.
export default function SoilStep({ soilTypes, soilType, setSoilType }) {
  const [preview, setPreview] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  // Free the preview image's memory when it changes or the component unmounts.
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  async function analyse(file) {
    if (!file) return;
    setError("");
    setPrediction(null);

    // Check on the client first: faster feedback, and no wasted upload.
    if (!file.type.startsWith("image/")) return setError("Please choose an image file.");
    if (file.size > MAX_BYTES) return setError("The photo is larger than 5 MB.");

    setPreview(URL.createObjectURL(file));
    setLoading(true);
    try {
      const result = await api.predictSoil(file);
      setPrediction(result);
      setSoilType(result.soil_type); // pre-select it; the user can still change it
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    analyse(e.dataTransfer.files?.[0]);
  }

  const soils = soilTypes.length ? soilTypes : Object.keys(SOILS);

  return (
    <StepCard number={1} title="Your soil" subtitle="Upload a photo of your soil, or pick the type yourself." done={!!soilType}>
      <div className="soil-layout">
        <label
          className={`dropzone ${dragging ? "is-dragging" : ""} ${preview ? "has-image" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          {preview ? (
            <img src={preview} alt="Your soil" />
          ) : (
            <span className="dropzone-text">
              <IconCamera width={28} height={28} />
              <b>Add a soil photo</b>
              <small>Click or drag an image here</small>
            </span>
          )}
          {loading && <span className="dropzone-overlay"><span className="spinner" /> Analysing…</span>}
          <input type="file" accept="image/*" onChange={(e) => analyse(e.target.files?.[0])} hidden />
        </label>

        <div className="soil-result">
          {prediction && (
            <div className={`detect ${prediction.low_confidence ? "is-unsure" : ""}`}>
              <p className="detect-title">
                Looks like <b>{SOILS[prediction.soil_type]?.en ?? prediction.soil_type} soil</b>
              </p>
              {/* One bar per soil type: shows how sure the model is, and what the runner-up was. */}
              <div className="prob-bars">
                {Object.entries(prediction.probabilities)
                  .sort((a, b) => b[1] - a[1])
                  .map(([name, p]) => (
                    <div className="prob-row" key={name}>
                      <span>{SOILS[name]?.en ?? name}</span>
                      <span className="prob-track"><span style={{ width: `${Math.round(p * 100)}%`, background: SOILS[name]?.color }} /></span>
                      <span className="prob-val">{Math.round(p * 100)}%</span>
                    </div>
                  ))}
              </div>
              {prediction.low_confidence && (
                <p className="detect-warn">The model is not sure. Please check the soil type below, or try a clearer photo in daylight.</p>
              )}
            </div>
          )}
          {error && <div className="notice error">{error}</div>}
          {!prediction && !error && <p className="muted small">The photo is optional — you can simply choose below.</p>}
        </div>
      </div>

      <div className="soil-picker" role="radiogroup" aria-label="Soil type">
        {soils.map((s) => {
          const info = SOILS[s] ?? { en: s, hi: "", color: "#999", note: "" };
          return (
            <button
              type="button"
              key={s}
              role="radio"
              aria-checked={soilType === s}
              className={`soil-option ${soilType === s ? "is-selected" : ""}`}
              onClick={() => setSoilType(soilType === s ? "" : s)}
            >
              <span className="swatch" style={{ background: info.color }} />
              <span className="soil-name">{info.en} <span className="hi">{info.hi}</span></span>
              <small>{info.note}</small>
            </button>
          );
        })}
      </div>
    </StepCard>
  );
}
