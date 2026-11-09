import { useLang } from "../i18n/useLang";
import { IconCheck } from "../components/Icons";

// The progress bar at the top of the advisor: 1 Soil - 2 Weather - 3 Soil test - 4 Results.
// Finished steps show a check mark; you can jump back to any step you can reach.
export default function Stepper({ steps, current, canOpen, onOpen }) {
  const { t } = useLang();
  return (
    <ol className="stepper">
      {steps.map((s, i) => {
        const state = i === current ? "current" : s.done ? "done" : "todo";
        return (
          <li key={s.key} className={`stepper-item is-${state}`}>
            <button
              type="button"
              onClick={() => onOpen(i)}
              disabled={!canOpen(i)}
              aria-current={i === current ? "step" : undefined}
            >
              <span className="stepper-dot">{s.done && i !== current ? <IconCheck width={14} height={14} /> : i + 1}</span>
              <span className="stepper-label">{t(s.key)}</span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
