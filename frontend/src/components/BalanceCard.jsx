import { useState } from "react";
import { formatBDT, PROVIDER_COLORS, PROVIDER_TEXT, CASH_COLOR } from "../lib/format";

export default function BalanceCard({ balances }) {
  const [expanded, setExpanded] = useState(false);

  if (!balances) return null;

  const providerTotal = Object.values(balances.providers).reduce((sum, p) => sum + p.balance, 0);
  const combinedTotal = balances.cash + providerTotal;

  return (
    <div className="balance-card">
      <button
        type="button"
        className="balance-card__combined"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
      >
        <div>
          <div className="eyebrow">Combined balance · cash + all providers</div>
          <div className="balance-total">{formatBDT(combinedTotal)}</div>
        </div>
        <span className={`expand-hint${expanded ? " expand-hint--open" : ""}`}>
          {expanded ? "Hide breakdown" : "Show per-provider breakdown"}
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>

      {expanded && (
        <div className="balance-card__breakdown">
          <div className="balance-row">
            <span className="badge" style={{ background: CASH_COLOR, color: PROVIDER_TEXT }}>Cash</span>
            <span className="balance-row__amount">{formatBDT(balances.cash)}</span>
          </div>
          {Object.entries(balances.providers).map(([provider, p]) => (
            <div className="balance-row" key={provider}>
              <span className="badge" style={{ background: PROVIDER_COLORS[provider], color: PROVIDER_TEXT }}>{provider}</span>
              <span className="balance-row__amount">{formatBDT(p.balance)}</span>
            </div>
          ))}
          <p className="hint-text">
            A healthy-looking combined total, or even a healthy single provider balance, can hide a
            shared-cash squeeze underneath — that's why the breakdown is one click away, not folded
            into a single number.
          </p>
        </div>
      )}
    </div>
  );
}
