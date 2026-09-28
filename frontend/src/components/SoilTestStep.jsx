import StepCard from "./StepCard";
import NumberField from "./NumberField";

// Step 3: soil test values, usually printed on the farmer's Soil Health Card.
// The hints show the range the model was trained on (from /meta).
export default function SoilTestStep({ values, setValue, ranges, done }) {
  // Ranges come as raw floats (e.g. 3.504752762); show at most 1 decimal.
  const fmt = (x) => Number(x.toFixed(1)).toString();
  const hint = (key) => {
    const r = ranges?.[key];
    return r ? `Usual range ${fmt(r[0])}–${fmt(r[1])}` : undefined;
  };

  return (
    <StepCard number={3} title="Soil test" subtitle="Copy these numbers from your Soil Health Card." done={done}>
      <div className="grid-4">
        <NumberField id="N" label="Nitrogen (N)" unit="kg/ha" min={0} max={500}
          value={values.N} onChange={(v) => setValue("N", v)} hint={hint("N")} />
        <NumberField id="P" label="Phosphorus (P)" unit="kg/ha" min={0} max={500}
          value={values.P} onChange={(v) => setValue("P", v)} hint={hint("P")} />
        <NumberField id="K" label="Potassium (K)" unit="kg/ha" min={0} max={500}
          value={values.K} onChange={(v) => setValue("K", v)} hint={hint("K")} />
        <NumberField id="ph" label="Soil pH" min={0} max={14} step="0.1"
          value={values.ph} onChange={(v) => setValue("ph", v)} hint={hint("ph")} />
      </div>
    </StepCard>
  );
}
