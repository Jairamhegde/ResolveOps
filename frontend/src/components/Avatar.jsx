import "./avatar.css";

const TONES = 8;

// The first letters of a name or email: "Priya Shah" -> "PS", "sam@acme.com" -> "S".
function initials(name) {
  const words = (name || "?").split("@")[0].split(/[\s._-]+/).filter(Boolean);
  return words
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join("");
}

// The same person always gets the same colour.
function tone(name) {
  let hash = 0;
  for (const char of name || "") hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return hash % TONES;
}

// A round initials avatar, like the reporter and assignee avatars in Jira.
function Avatar({ name, size = "small" }) {
  return (
    <span className={`avatar avatar-${size} avatar-tone-${tone(name)}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

// An avatar with the name beside it.
export function Person({ name }) {
  if (!name) return <span className="person person-unknown">Unknown</span>;
  return (
    <span className="person">
      <Avatar name={name} />
      <span className="person-name">{name}</span>
    </span>
  );
}

export default Avatar;
