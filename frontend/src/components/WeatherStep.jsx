import { useState } from "react";
import { api } from "../api";
import StepCard from "./StepCard";
import NumberField from "./NumberField";
import { IconDrop, IconPin, IconRain, IconSearch, IconThermo } from "./Icons";

// Step 2: weather. Search a place -> fetch the last 30 days -> fill the fields.
// The fields stay editable, because the rainfall value is only an estimate.
export default function WeatherStep({ values, setValue, done }) {
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState(null);
  const [chosen, setChosen] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search() {
    if (query.trim().length < 2) return setError("Type at least 2 letters.");
    setError("");
    setInfo(null);
    setChosen(null);
    setPlaces(null);
    setLoading(true);
    let found;
    try {
      found = await api.places(query.trim());
    } catch (err) {
      setError(err.message);
      setLoading(false);
      return;
    }
    setLoading(false);
    // Exactly one match (the usual case): pick it straight away, no extra click.
    // Several matches (e.g. "Rampur" exists in many states): let the user choose.
    if (found.length === 1) {
      choose(found[0]);
    } else {
      setPlaces(found);
    }
  }

  async function choose(place) {
    setChosen(place);
    setPlaces(null);
    setError("");
    setLoading(true);
    try {
      const w = await api.weather(place.latitude, place.longitude);
      setValue("temperature", String(w.temperature));
      setValue("humidity", String(w.humidity));
      setValue("rainfall", String(w.rainfall));
      setInfo(w);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const label = (p) => [p.name, p.district !== p.name ? p.district : null, p.state].filter(Boolean).join(", ");
  const fmtDate = (d) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });

  return (
    <StepCard number={2} title="Weather" subtitle="Type your village or town and we'll fill in the last 30 days of weather." done={done}>
      {/* Not a <form>: this whole step already sits inside App's form, and
          HTML does not allow a form inside a form. Enter is handled by hand. */}
      <div className="search">
        <span className="search-icon"><IconPin /></span>
        <input
          aria-label="Village or town"
          placeholder="e.g. Begusarai"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault(); // don't submit the main form
              search();
            }
          }}
        />
        <button type="button" className="btn-secondary" onClick={search} disabled={loading}>
          {loading ? <span className="spinner dark" /> : <IconSearch width={18} height={18} />}
          <span>Find</span>
        </button>
      </div>

      {loading && <p className="muted small">{chosen ? "Getting the weather…" : "Searching…"}</p>}
      {places && places.length === 0 && <div className="notice warn">No place found. Check the spelling.</div>}
      {places && places.length > 1 && <p className="muted small">Several places match — pick yours:</p>}
      {places && places.length > 0 && (
        <ul className="places">
          {places.map((p) => (
            <li key={`${p.latitude},${p.longitude}`}>
              <button type="button" onClick={() => choose(p)}><IconPin width={14} height={14} /> {label(p)}</button>
            </li>
          ))}
        </ul>
      )}
      {error && <div className="notice error">{error}</div>}
      {info && chosen && (
        <div className="weather-source">
          <IconPin width={16} height={16} />
          <span>
            <b>{label(chosen)}</b> · {fmtDate(info.period.start)} – {fmtDate(info.period.end)}
            <small>{info.note}</small>
          </span>
        </div>
      )}

      <div className="grid-3">
        <NumberField id="temperature" label="Temperature" icon={<IconThermo />} unit="°C" min={-10} max={60}
          value={values.temperature} onChange={(v) => setValue("temperature", v)} />
        <NumberField id="humidity" label="Humidity" icon={<IconDrop />} unit="%" min={0} max={100}
          value={values.humidity} onChange={(v) => setValue("humidity", v)} />
        <NumberField id="rainfall" label="Rainfall" icon={<IconRain />} unit="mm" min={0} max={5000}
          value={values.rainfall} onChange={(v) => setValue("rainfall", v)} />
      </div>
    </StepCard>
  );
}
