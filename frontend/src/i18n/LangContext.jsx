import { useEffect, useState } from "react";
import { STRINGS } from "./strings";
import { LangContext } from "./useLang";

// English / Hindi switch. Components read it with useLang() (see ./useLang.js)
// and write t("some.key") instead of hard-coded text.

function savedLang() {
  try {
    return localStorage.getItem("km-lang") === "hi" ? "hi" : "en";
  } catch {
    return "en"; // storage can be blocked (private mode) - just use English
  }
}

export function LangProvider({ children }) {
  const [lang, setLang] = useState(savedLang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem("km-lang", lang);
    } catch {
      /* not critical */
    }
  }, [lang]);

  // t("home.cta") -> text in the current language (falls back to English).
  // t("weather.years", { start: 2021 }) fills in {start}.
  const t = (key, vars) => {
    let text = STRINGS[lang][key] ?? STRINGS.en[key] ?? key;
    if (vars) for (const [k, v] of Object.entries(vars)) text = text.replaceAll(`{${k}}`, v);
    return text;
  };

  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}
