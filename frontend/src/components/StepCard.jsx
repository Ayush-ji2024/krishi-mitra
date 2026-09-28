import { IconCheck } from "./Icons";

// A numbered step. When `done` is true the number turns into a check mark,
// so the farmer can see at a glance what is still missing.
export default function StepCard({ number, title, subtitle, done, children }) {
  return (
    <section className={`step-card ${done ? "is-done" : ""}`}>
      <div className="step-head">
        <span className="step-badge" aria-hidden="true">{done ? <IconCheck width={16} height={16} /> : number}</span>
        <div>
          <h2>{title}</h2>
          {subtitle && <p className="step-sub">{subtitle}</p>}
        </div>
      </div>
      <div className="step-body">{children}</div>
    </section>
  );
}
