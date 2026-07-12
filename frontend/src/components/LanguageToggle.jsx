import { LANGUAGES, useLanguage } from "../lib/language-context";

export default function LanguageToggle() {
  const { lang, setLang } = useLanguage();
  return (
    <div className="lang-toggle" role="group" aria-label="Language">
      {LANGUAGES.map((l) => (
        <button
          key={l.code}
          className={l.code === lang ? "lang-btn active" : "lang-btn"}
          onClick={() => setLang(l.code)}
          type="button"
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}
