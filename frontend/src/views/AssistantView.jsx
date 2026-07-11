import { useState } from "react";
import { askChat } from "../api";
import { useLanguage } from "../lib/LanguageContext";

// The three queries section 10 requires this stage to support, offered as
// one-click prompts so a demo doesn't depend on typing.
const SAMPLES = [
  "why is bKash at risk",
  "which provider needs attention",
  "what should we do next",
];

export default function AssistantView({ split }) {
  const { lang } = useLanguage();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(q) {
    const text = (q ?? question).trim();
    if (!text || loading) return;
    setQuestion(text);
    setLoading(true);
    setError("");
    setAnswer("");
    try {
      const { answer: reply } = await askChat(text, lang, split);
      setAnswer(reply);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="view">
      <p className="risk-notice">
        Ask about current open alerts, balances, or which provider needs attention. This assistant
        is <strong>read-only</strong> — it reports on what the system already computed and never
        creates an alert, changes a case, or makes a new recommendation.
      </p>

      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. why is bKash at risk"
          aria-label="Ask a question"
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? "Asking…" : "Ask"}
        </button>
      </form>

      <div className="chat-samples">
        {SAMPLES.map((s) => (
          <button key={s} type="button" className="chat-sample" onClick={() => ask(s)} disabled={loading}>
            {s}
          </button>
        ))}
      </div>

      {error && <p className="error-text">{error}</p>}
      {answer && <div className="chat-answer">{answer}</div>}
    </div>
  );
}
