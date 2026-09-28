// Small inline SVG icons (no icon library needed). They inherit the text colour.
const base = {
  width: 20, height: 20, viewBox: "0 0 24 24", fill: "none",
  stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round",
  "aria-hidden": true, focusable: false,
};

export const IconCamera = (p) => (
  <svg {...base} {...p}><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></svg>
);
export const IconPin = (p) => (
  <svg {...base} {...p}><path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" /><circle cx="12" cy="9.5" r="2.5" /></svg>
);
export const IconSearch = (p) => (
  <svg {...base} {...p}><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></svg>
);
export const IconThermo = (p) => (
  <svg {...base} {...p}><path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z" /></svg>
);
export const IconDrop = (p) => (
  <svg {...base} {...p}><path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z" /></svg>
);
export const IconRain = (p) => (
  <svg {...base} {...p}><path d="M7 15a4 4 0 1 1 .9-7.9A5.5 5.5 0 0 1 18.5 9 3.5 3.5 0 0 1 17 15.9" /><path d="m9 18-1 2m5-2-1 2m5-2-1 2" /></svg>
);
export const IconFlask = (p) => (
  <svg {...base} {...p}><path d="M9 3h6m-5 0v6L4.5 19A1.5 1.5 0 0 0 5.8 21h12.4a1.5 1.5 0 0 0 1.3-2L14 9V3" /><path d="M7 15h10" /></svg>
);
export const IconSprout = (p) => (
  <svg {...base} {...p}><path d="M12 21v-9" /><path d="M12 12c0-4 3-6 7-6 0 4-3 6-7 6z" /><path d="M12 14c0-3-2.5-5-6-5 0 3 2.5 5 6 5z" /></svg>
);
export const IconCheck = (p) => (
  <svg {...base} strokeWidth={3} {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></svg>
);
export const IconAlert = (p) => (
  <svg {...base} {...p}><path d="M12 3 2 20h20z" /><path d="M12 10v4m0 3v.01" /></svg>
);
export const IconArrowRight = (p) => (
  <svg {...base} {...p}><path d="M5 12h14m-6-6 6 6-6 6" /></svg>
);
export const IconArrowLeft = (p) => (
  <svg {...base} {...p}><path d="M19 12H5m6-6-6 6 6 6" /></svg>
);
export const IconMenu = (p) => (
  <svg {...base} {...p}><path d="M4 7h16M4 12h16M4 17h16" /></svg>
);
export const IconClose = (p) => (
  <svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const IconShield = (p) => (
  <svg {...base} {...p}><path d="M12 3 4.5 6v5.5c0 4.5 3.2 8.2 7.5 9.5 4.3-1.3 7.5-5 7.5-9.5V6z" /><path d="m9 12 2 2 4-4" /></svg>
);
export const IconRefresh = (p) => (
  <svg {...base} {...p}><path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 4v7h-7" /></svg>
);
export const IconGithub = (p) => (
  <svg {...base} {...p}><path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21" /></svg>
);
