import { cropInfo, SOILS } from "../data";
import { IconAlert, IconSprout } from "./Icons";

// Shows the recommendations in plain words.
// NOTE: "score" is only used for ORDER. We never show it as a percentage,
// because "0.7" would be misread as "70% chance" (it is probability x soil weight).

function matchInfo(p) {
  if (p >= 0.7) return { text: "Strong match", level: 3, cls: "good" };
  if (p >= 0.3) return { text: "Possible match", level: 2, cls: "mid" };
  return { text: "Weak match", level: 1, cls: "low" };
}

const SOIL_TEXT = {
  good: { text: "Grows well in your soil", cls: "good" },
  possible: { text: "Can grow in your soil", cls: "mid" },
  poor: { text: "Not ideal for your soil", cls: "low" },
};

export default function Results({ result, soilType, loading }) {
  if (loading) {
    return (
      <aside className="plan">
        <h2 className="plan-title">Your crop plan</h2>
        <div className="plan-empty"><span className="spinner dark big" /><p>Thinking…</p></div>
      </aside>
    );
  }

  if (!result) {
    return (
      <aside className="plan">
        <h2 className="plan-title">Your crop plan</h2>
        <div className="plan-empty">
          <span className="plan-empty-icon"><IconSprout width={36} height={36} /></span>
          <p>Fill in the three steps and press <b>Suggest crops</b>. Your best crops will appear here.</p>
        </div>
      </aside>
    );
  }

  const allWeak = result.recommendations.every((r) => r.probability < 0.3);

  return (
    <aside className="plan" aria-live="polite">
      <h2 className="plan-title">Your crop plan</h2>
      {soilType && <p className="muted small">For <b>{SOILS[soilType]?.en ?? soilType}</b> soil</p>}

      {allWeak && (
        <div className="notice warn">
          None of the crops is a strong fit for these values. Please double-check your soil test numbers.
        </div>
      )}

      <ol className="crop-list">
        {result.recommendations.map((r, i) => {
          const crop = cropInfo(r.crop);
          const match = matchInfo(r.probability);
          const soil = r.soil_suitability && SOIL_TEXT[r.soil_suitability];
          return (
            <li key={r.crop} className={`crop-card ${i === 0 ? "is-top" : ""}`}>
              {i === 0 && <span className="ribbon">Best choice</span>}
              <span className="crop-emoji" aria-hidden="true">{crop.emoji}</span>
              <div className="crop-main">
                <div className="crop-name">
                  {crop.en} {crop.hi && <span className="hi">{crop.hi}</span>}
                </div>
                <div className="meter" title={match.text}>
                  {[1, 2, 3].map((n) => (
                    <span key={n} className={n <= match.level ? `on ${match.cls}` : ""} />
                  ))}
                  <span className="meter-label">{match.text}</span>
                </div>
                {soil && <span className={`pill ${soil.cls}`}>{soil.text}</span>}
              </div>
            </li>
          );
        })}
      </ol>

      {result.warnings.length > 0 && (
        <div className="notice warn">
          <IconAlert width={16} height={16} /> <b>Please note</b>
          <ul>{result.warnings.map((w) => <li key={w}>{w}</li>)}</ul>
        </div>
      )}

      <p className="disclaimer">
        Suggestions come from a model trained on a public dataset and FAO soil data.
        Please confirm with your local Krishi Vigyan Kendra before sowing.
      </p>
    </aside>
  );
}
