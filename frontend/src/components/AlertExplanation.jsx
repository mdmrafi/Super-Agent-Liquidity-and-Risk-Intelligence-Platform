import { useEffect, useState } from "react";
import { useLanguage } from "../lib/LanguageContext";

/** Stage 5: a natural-language sentence derived from the alert object via
 *  explain_alert() (real LLM call, with a server-side plain-template
 *  fallback on failure -- see explain/explain.py). This is additional to
 *  the evidence array, never a replacement for it -- evidence stays
 *  verbatim elsewhere on the card regardless of language.
 *
 *  Lazy by design: this is a real LLM call, and list views can render
 *  hundreds of cards at once. Fetching on mount for every card would queue
 *  hundreds of API calls nobody asked for. Revealed on click; once revealed,
 *  switching languages refetches automatically. */
export default function AlertExplanation({ alertId, split }) {
  const { lang, explain } = useLanguage();
  const [revealed, setRevealed] = useState(false);
  const [text, setText] = useState(null);

  useEffect(() => {
    if (!revealed) return;
    let cancelled = false;
    setText(null);
    explain(alertId, split).then((v) => {
      if (!cancelled) setText(v);
    });
    return () => {
      cancelled = true;
    };
  }, [revealed, alertId, split, lang, explain]);

  if (!revealed) {
    return (
      <button type="button" className="explain-toggle" onClick={() => setRevealed(true)}>
        Explain in plain language
      </button>
    );
  }

  return <p className="alert-explanation">{text ?? "…"}</p>;
}
