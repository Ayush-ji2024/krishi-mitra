import { useState } from "react";

// All the advisor's data lives here, in the App, so it survives when the user
// visits another page (Home / About) and comes back.
export const WEATHER_FIELDS = ["temperature", "humidity", "rainfall"];
export const TEST_FIELDS = ["N", "P", "K", "ph"];
export const ALL_FIELDS = [...TEST_FIELDS, ...WEATHER_FIELDS];
const EMPTY = Object.fromEntries(ALL_FIELDS.map((f) => [f, ""]));

export function useAdvisor() {
  const [step, setStep] = useState(0);             // 0 soil, 1 weather, 2 soil test, 3 results
  const [soilType, setSoilTypeRaw] = useState("");
  const [photo, setPhoto] = useState(null);        // { url, prediction }
  const [values, setValues] = useState(EMPTY);     // the 7 numbers, as strings while typing
  const [place, setPlace] = useState(null);        // { place, weather } after a successful lookup
  const [season, setSeason] = useState("");        // "kharif" | "rabi" | "zaid" (set from the weather lookup)
  const [result, setResult] = useState(null);

  // Any change to the inputs makes old results out of date.
  const setSoilType = (s) => { setSoilTypeRaw(s); setResult(null); };
  const setValue = (field, value) => {
    setValues((old) => ({ ...old, [field]: value }));
    setResult(null);
  };
  const setMany = (obj) => {
    setValues((old) => ({ ...old, ...obj }));
    setResult(null);
  };

  const filled = (fields) => fields.every((f) => values[f] !== "");

  function reset() {
    if (photo?.url) URL.revokeObjectURL(photo.url);
    setStep(0);
    setSoilTypeRaw("");
    setPhoto(null);
    setValues(EMPTY);
    setPlace(null);
    setSeason("");
    setResult(null);
  }

  return {
    step, setStep, soilType, setSoilType, photo, setPhoto,
    values, setValue, setMany, filled, place, setPlace, season, setSeason, result, setResult, reset,
  };
}
