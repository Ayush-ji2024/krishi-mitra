import { useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n/useLang";
import NumberField from "../components/NumberField";
import { IconDrop, IconPin, IconRain, IconSearch, IconThermo } from "../components/Icons";

// Step 2: weather. Search a place -> fetch the last 30 days -> fill the fields.
// The fields stay editable, because the rainfall value is only an estimate.
export default function WeatherStep({ advisor }) {
  const { t, lang } = useLang();
  const { values, setValue, place, setPlace } = advisor;
  const [query, setQuery] = useState(place?.place.name ?? "");
  const [matches, setMatches] = useState(null);
  const [status, setStatus] = useState("");   // "", "searching", "getting"
  const [error, setError] = useState("");

  async function search() {
    if (query.trim().length < 2) return setError(t("weather.min2"));
    setError("");
    setMatches(null);
    setStatus("searching");
    let found;
    try {
      found = await api.places(query.trim());
    } catch (err) {
      setError(err.message);
      setStatus("");
      return;
    }
    setStatus("");
    // Exactly one match (the usual case): pick it straight away, no extra click.
    // Several matches (e.g. "Rampur" exists in many states): let the user choose.
    if (found.length === 1) choose(found[0]);
    else setMatches(found);
  }

  async function choose(p) {
    setMatches(null);
    setError("");
    setStatus("getting");
    try {
      const w = await api.weather(p.latitude, p.longitude);
      setValue("temperature", String(w.temperature));
      setValue("humidity", String(w.humidity));
      setValue("rainfall", String(w.rainfall));
      setPlace({ place: p, weather: w });
    } catch (err) {
      setError(err.message);
    } finally {
      setStatus("");
    }
  }

  const label = (p) => [p.name, p.district !== p.name ? p.district : null, p.state].filter(Boolean).join(", ");
  const fmtDate = (d) => new Date(d).toLocaleDateString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short" });
  const busy = status !== "";

  return (
    <div className="step-panel">
      <h1 className="step-title">{t("weather.title")}</h1>
      <p className="step-sub">{t("weather.sub")}</p>

      {/* Not a <form>: Enter is handled by hand so it never submits anything else. */}
      <div className="search">
        <span className="search-icon"><IconPin /></span>
        <input
          aria-label={t("weather.placeholder")}
          placeholder={t("weather.placeholder")}
          value={query}
          enterKeyHint="search"
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              search();
            }
          }}
        />
        <button type="button" className="btn btn-outline" onClick={search} disabled={busy}>
          {busy ? <span className="spinner dark" /> : <IconSearch width={18} height={18} />}
          <span className="hide-xs">{t("weather.find")}</span>
        </button>
      </div>

      {busy && <p className="muted small">{status === "getting" ? t("weather.getting") : t("weather.searching")}</p>}
      {matches && matches.length === 0 && <div className="notice warn">{t("weather.none")}</div>}
      {matches && matches.length > 1 && <p className="muted small">{t("weather.several")}</p>}
      {matches && matches.length > 0 && (
        <ul className="places">
          {matches.map((p) => (
            <li key={`${p.latitude},${p.longitude}`}>
              <button type="button" onClick={() => choose(p)}><IconPin width={14} height={14} /> {label(p)}</button>
            </li>
          ))}
        </ul>
      )}
      {error && <div className="notice error">{error}</div>}

      {place && !busy && (
        <div className="weather-card">
          <div className="weather-card-head">
            <IconPin width={18} height={18} />
            <div>
              <b>{label(place.place)}</b>
              <small>{t("weather.period", { start: fmtDate(place.weather.period.start), end: fmtDate(place.weather.period.end) })}</small>
            </div>
          </div>
          <small className="weather-note">{t("weather.estimate")}</small>
        </div>
      )}

      <p className="label-strong">{t("weather.manual")}</p>
      <div className="grid-3">
        <NumberField id="temperature" label={t("weather.temperature")} icon={<IconThermo />} unit="°C" min={-10} max={60}
          value={values.temperature} onChange={(v) => setValue("temperature", v)} />
        <NumberField id="humidity" label={t("weather.humidity")} icon={<IconDrop />} unit="%" min={0} max={100}
          value={values.humidity} onChange={(v) => setValue("humidity", v)} />
        <NumberField id="rainfall" label={t("weather.rainfall")} icon={<IconRain />} unit="mm" min={0} max={5000}
          value={values.rainfall} onChange={(v) => setValue("rainfall", v)} />
      </div>
    </div>
  );
}
