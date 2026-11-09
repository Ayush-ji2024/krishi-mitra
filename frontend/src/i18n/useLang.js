import { createContext, useContext } from "react";

// The language context and its hook live in their own file (not next to the
// <LangProvider> component) so React Fast Refresh keeps working.
// Any component can call `const { t, lang } = useLang()`.
export const LangContext = createContext(null);

export const useLang = () => useContext(LangContext);
