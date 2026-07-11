import { useState } from "react";
import { formatBDT, PROVIDER_COLORS } from "../lib/format";

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
          <div className="muted">Combined balance (cash + all providers)</div>
          <div className="balance-total">{formatBDT(combinedTotal)}</div>
        </div>
        <span className="expand-hint">{expanded ? "▲ hide breakdown" : "▼ show per-provider breakdown"}</span>
      </button>

      {expanded && (
        <div className="balance-card__breakdown">
          <div className="balance-row">
            <span className="badge" style={{ background: "#495057" }}>Cash</span>
            <span>{formatBDT(balances.cash)}</span>
          </div>
          {Object.entries(balances.providers).map(([provider, p]) => (
            <div className="balance-row" key={provider}>
              <span className="badge" style={{ background: PROVIDER_COLORS[provider] }}>{provider}</span>
              <span>{formatBDT(p.balance)}</span>
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
