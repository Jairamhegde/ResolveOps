// Small line icons drawn on a 16px grid. They take the text colour, so they work in light and dark mode.

function Icon({ children, className = "icon", ...props }) {
  return (
    <svg
      className={className}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function OverviewIcon() {
  return (
    <Icon>
      <rect x="2" y="2" width="5" height="6" rx="1" />
      <rect x="9" y="2" width="5" height="3.5" rx="1" />
      <rect x="2" y="10.5" width="5" height="3.5" rx="1" />
      <rect x="9" y="8" width="5" height="6" rx="1" />
    </Icon>
  );
}

export function TicketsIcon() {
  return (
    <Icon>
      <path d="M2 4.5A1.5 1.5 0 0 1 3.5 3h9A1.5 1.5 0 0 1 14 4.5V6a2 2 0 0 0 0 4v1.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 2 11.5V10a2 2 0 0 0 0-4z" />
      <path d="M10 3v10" strokeDasharray="1.5 1.5" />
    </Icon>
  );
}

export function PeopleIcon() {
  return (
    <Icon>
      <circle cx="6" cy="5.5" r="2.5" />
      <path d="M1.5 13.5c.4-2.4 2.2-4 4.5-4s4.1 1.6 4.5 4" />
      <path d="M10.5 3.2a2.5 2.5 0 0 1 0 4.6M12 9.8c1.3.5 2.2 1.9 2.5 3.7" />
    </Icon>
  );
}

export function ShieldIcon() {
  return (
    <Icon>
      <path d="M8 1.8 13.5 4v4c0 3.2-2.3 5.4-5.5 6.2C4.8 13.4 2.5 11.2 2.5 8V4z" />
      <path d="m5.8 8 1.5 1.5L10.4 6.4" />
    </Icon>
  );
}

export function LogOutIcon() {
  return (
    <Icon>
      <path d="M6 2.5H3.5a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1H6" />
      <path d="M10.5 11 13.5 8l-3-3M13.5 8H6" />
    </Icon>
  );
}

export function SearchIcon() {
  return (
    <Icon>
      <circle cx="7" cy="7" r="4.5" />
      <path d="m10.5 10.5 3 3" />
    </Icon>
  );
}

export function CloseIcon() {
  return (
    <Icon>
      <path d="m4 4 8 8M12 4l-8 8" />
    </Icon>
  );
}

export function SunIcon() {
  return (
    <Icon>
      <circle cx="8" cy="8" r="3" />
      <path d="M8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1" />
    </Icon>
  );
}

export function MoonIcon() {
  return (
    <Icon>
      <path d="M13.5 9.5A5.5 5.5 0 0 1 6.5 2.5a5.5 5.5 0 1 0 7 7z" />
    </Icon>
  );
}

// The sparkle used next to anything the AI did.
export function SparkleIcon() {
  return (
    <Icon strokeWidth="1.3">
      <path d="M8 1.5c.4 3.2 1.8 5.1 5 6.5-3.2 1.4-4.6 3.3-5 6.5-.4-3.2-1.8-5.1-5-6.5 3.2-1.4 4.6-3.3 5-6.5z" fill="currentColor" />
    </Icon>
  );
}

// Jira-style priority arrows: the shape says how urgent, so it reads without colour too.
const PRIORITY_PATHS = {
  critical: ["M3.5 8.5 8 4l4.5 4.5", "M3.5 12.5 8 8l4.5 4.5"],
  high: ["M3.5 10.5 8 6l4.5 4.5"],
  medium: ["M3.5 6.5h9", "M3.5 10h9"],
  low: ["M3.5 6 8 10.5 12.5 6"],
  minimal: ["M3.5 3.5 8 8l4.5-4.5", "M3.5 7.5 8 12l4.5-4.5"],
};

export function PriorityIcon({ level }) {
  return (
    <Icon className="icon priority-icon" strokeWidth="2">
      {(PRIORITY_PATHS[level] || PRIORITY_PATHS.medium).map((path) => (
        <path key={path} d={path} />
      ))}
    </Icon>
  );
}

// The ResolveOps mark: a white ticket on a blue tile, the same shape as the favicon.
export function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path d="M9 10h14v4.5a2 2 0 0 0 0 3V22H9v-4.5a2 2 0 0 0 0-3z" fill="var(--on-brand)" />
    </svg>
  );
}
