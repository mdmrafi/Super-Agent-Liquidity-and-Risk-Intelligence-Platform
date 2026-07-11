const common = {
  width: 18,
  height: 18,
  viewBox: "0 0 20 20",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function IconAgent(props) {
  return (
    <svg {...common} {...props}>
      <circle cx="10" cy="6.5" r="3.2" />
      <path d="M3.5 17c.9-3.4 3.6-5.2 6.5-5.2s5.6 1.8 6.5 5.2" />
    </svg>
  );
}

export function IconOps(props) {
  return (
    <svg {...common} {...props}>
      <rect x="3.2" y="3.2" width="13.6" height="13.6" rx="2.6" />
      <path d="M6.8 10.3l2.1 2.1 4.3-4.6" />
    </svg>
  );
}

export function IconProvider(props) {
  return (
    <svg {...common} {...props}>
      <path d="M4 17V7.5L10 3l6 4.5V17" />
      <path d="M4 17h12" />
      <path d="M8 17v-4h4v4" />
    </svg>
  );
}

export function IconRisk(props) {
  return (
    <svg {...common} {...props}>
      <path d="M10 2.8l6 2.2v4.4c0 4-2.6 6.8-6 7.8-3.4-1-6-3.8-6-7.8V5l6-2.2z" />
      <path d="M10 9v3.2" />
      <circle cx="10" cy="14.4" r="0.15" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconAssistant(props) {
  return (
    <svg {...common} {...props}>
      <path d="M3.5 5.6c0-1.2 1-2.1 2.1-2.1h8.8c1.2 0 2.1 1 2.1 2.1v6c0 1.2-1 2.1-2.1 2.1H8.4L5 17v-3.3H5.6c-1.2 0-2.1-1-2.1-2.1z" />
      <path d="M7 8h6M7 10.6h4" />
    </svg>
  );
}

export function IconChevron(props) {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true" {...props}>
      <path d="M4 6l4 4 4-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function IconAlertCircle(props) {
  return (
    <svg {...common} {...props}>
      <circle cx="10" cy="10" r="7.2" />
      <path d="M10 6.6v4" />
      <circle cx="10" cy="13.4" r="0.15" fill="currentColor" stroke="none" />
    </svg>
  );
}

export function IconInbox(props) {
  return (
    <svg {...common} {...props}>
      <path d="M3.3 11.5L5.4 4.6h9.2l2.1 6.9" />
      <path d="M3.3 11.5v3a1.4 1.4 0 0 0 1.4 1.4h10.6a1.4 1.4 0 0 0 1.4-1.4v-3h-4.3l-.9 1.8H8.5l-.9-1.8z" />
    </svg>
  );
}
