// Display info for soils and crops: English + Hindi names, colours and emoji.
// Kept in one place so the components stay about layout and logic.

export const SOILS = {
  alluvial: { en: "Alluvial", hi: "जलोढ़", color: "#b89266", note: { en: "River plains, loamy", hi: "नदी के मैदान, दोमट" } },
  black:    { en: "Black",    hi: "काली",  color: "#2e2724", note: { en: "Fine, holds water",   hi: "बारीक, पानी रोकती है" } },
  clay:     { en: "Clay",     hi: "चिकनी", color: "#8c6f5c", note: { en: "Heavy, sticky",       hi: "भारी, चिपचिपी" } },
  red:      { en: "Red",      hi: "लाल",   color: "#a8472b", note: { en: "Sandy, porous",       hi: "रेतीली, भुरभुरी" } },
};

export const CROPS = {
  rice:        { en: "Rice",         hi: "धान",     emoji: "🌾" },
  maize:       { en: "Maize",        hi: "मक्का",   emoji: "🌽" },
  chickpea:    { en: "Chickpea",     hi: "चना",     emoji: "🫘" },
  kidneybeans: { en: "Kidney beans", hi: "राजमा",   emoji: "🫘" },
  pigeonpeas:  { en: "Pigeon peas",  hi: "अरहर",    emoji: "🫛" },
  mothbeans:   { en: "Moth beans",   hi: "मोठ",     emoji: "🫘" },
  mungbean:    { en: "Mung bean",    hi: "मूंग",    emoji: "🫛" },
  blackgram:   { en: "Black gram",   hi: "उड़द",    emoji: "🫘" },
  lentil:      { en: "Lentil",       hi: "मसूर",    emoji: "🫘" },
  pomegranate: { en: "Pomegranate",  hi: "अनार",    emoji: "🍎" },
  banana:      { en: "Banana",       hi: "केला",    emoji: "🍌" },
  mango:       { en: "Mango",        hi: "आम",      emoji: "🥭" },
  grapes:      { en: "Grapes",       hi: "अंगूर",   emoji: "🍇" },
  watermelon:  { en: "Watermelon",   hi: "तरबूज",   emoji: "🍉" },
  muskmelon:   { en: "Muskmelon",    hi: "खरबूजा",  emoji: "🍈" },
  apple:       { en: "Apple",        hi: "सेब",     emoji: "🍎" },
  orange:      { en: "Orange",       hi: "संतरा",   emoji: "🍊" },
  papaya:      { en: "Papaya",       hi: "पपीता",   emoji: "🌳" },
  coconut:     { en: "Coconut",      hi: "नारियल",  emoji: "🥥" },
  cotton:      { en: "Cotton",       hi: "कपास",    emoji: "☁️" },
  jute:        { en: "Jute",         hi: "जूट",     emoji: "🌿" },
  coffee:      { en: "Coffee",       hi: "कॉफ़ी",   emoji: "☕" },
};

// Fallback for any crop not in the list (e.g. if the model is retrained later).
export const cropInfo = (name) =>
  CROPS[name] ?? { en: name[0].toUpperCase() + name.slice(1), hi: "", emoji: "🌱" };

// Main name in the chosen language + the other language as a small subtitle.
export function names(item, lang) {
  return lang === "hi" ? { main: item.hi || item.en, sub: item.en } : { main: item.en, sub: item.hi };
}

// A realistic sample (the first row of the Kaggle dataset - a "rice" field),
// so anyone can try the app without a Soil Health Card.
export const SAMPLE_SOIL_TEST = { N: "90", P: "42", K: "43", ph: "6.5" };
