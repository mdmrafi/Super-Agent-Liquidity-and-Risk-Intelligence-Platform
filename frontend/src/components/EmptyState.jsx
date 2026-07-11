import { IconInbox } from "./icons";

export default function EmptyState({ title = "Nothing here", hint }) {
  return (
    <div className="empty-state">
      <IconInbox className="empty-state__icon" />
      <p className="empty-state__title">{title}</p>
      {hint && <p className="muted">{hint}</p>}
    </div>
  );
}
