import { createContext, useContext } from "react";

export const LanguageContext = createContext(null);

export const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "bn", label: "বাংলা" },
  { code: "banglish", label: "Banglish" },
];

export function useLanguage() {
  return useContext(LanguageContext);
}
