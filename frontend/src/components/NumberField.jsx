// One labelled number input, with an optional icon, unit and hint.
// The value stays a STRING while typing (so "6." or an empty box are allowed);
// pages/Advisor.jsx converts it to a number on submit.
export default function NumberField({ id, label, icon, unit, value, onChange, min, max, step = "any", hint }) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <div className="input-wrap">
        {icon && <span className="input-icon">{icon}</span>}
        <input
          id={id}
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          placeholder="—"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={icon ? "has-icon" : ""}
        />
        {unit && <span className="input-unit">{unit}</span>}
      </div>
      {hint && <small className="hint">{hint}</small>}
    </div>
  );
}
