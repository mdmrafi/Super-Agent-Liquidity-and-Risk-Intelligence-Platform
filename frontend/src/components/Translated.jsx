import { useEffect, useState } from "react";
import { useLanguage } from "../lib/LanguageContext";

/** Renders text through the (currently placeholder) translate function.
 *  Stage 5 swaps the backend implementation only -- this component doesn't change. */
export default function Translated({ text }) {
  const { t, lang } = useLanguage();
  const [out, setOut] = useState(text);

  useEffect(() => {
    let cancelled = false;
    t(text).then((v) => {
      if (!cancelled) setOut(v);
    });
    return () => {
      cancelled = true;
    };
  }, [text, lang, t]);

  return <>{out}</>;
}
