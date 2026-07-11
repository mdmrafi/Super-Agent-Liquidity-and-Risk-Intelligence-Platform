import { createContext, useContext, useState, useCallback } from "react";
import { translate } from "../api";

const LanguageContext = createContext(null);

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা" },
  { code: "bn-latn", label: "Banglish" },
];

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en");
  const [cache] = useState(() => new Map());

  const t = useCallback(
    async (text) => {
      if (lang === "en") return text;
      const key = `${lang}::${text}`;
      if (cache.has(key)) return cache.get(key);
      const { translated } = await translate(text, lang);
      cache.set(key, translated);
      return translated;
    },
    [lang, cache]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
