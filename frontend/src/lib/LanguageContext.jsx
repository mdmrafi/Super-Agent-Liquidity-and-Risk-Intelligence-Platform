import { createContext, useContext, useState, useCallback } from "react";
import { explainAlert } from "../api";

const LanguageContext = createContext(null);

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা" },
  { code: "banglish", label: "Banglish" },
];

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en");
  const [cache] = useState(() => new Map());

  const explain = useCallback(
    async (alertId, split) => {
      const key = `${lang}::${split}::${alertId}`;
      if (cache.has(key)) return cache.get(key);
      const { explanation } = await explainAlert(alertId, lang, split);
      cache.set(key, explanation);
      return explanation;
    },
    [lang, cache]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang, explain }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
