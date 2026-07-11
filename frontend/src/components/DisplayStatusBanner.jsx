/** Purely informational. Never disables anything else on the page --
 *  see App.css: no rule here ever sets `disabled` on a sibling control. */
export default function DisplayStatusBanner({ status }) {
  if (status === "normal") return null;
  return (
    <div className="status-banner" role="status">
      <strong>{status}</strong> — replenishment support has been requested. The agent continues to
      operate normally; this clears automatically once the case is resolved.
    </div>
  );
}
