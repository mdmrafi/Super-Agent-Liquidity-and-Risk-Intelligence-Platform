import { useState, useCallback } from "react";
import { explainAlert } from "../api";
import { LanguageContext } from "./language-context";

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
