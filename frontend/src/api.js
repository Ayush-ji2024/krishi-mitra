// All communication with the FastAPI backend lives in this one file.
// The backend address comes from the VITE_API_URL environment variable
// (see .env.example); locally it defaults to the uvicorn dev server.
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, options);
  } catch {
    // fetch() only throws when the server can't be reached at all.
    throw new Error(`Cannot reach the server at ${API_URL || "this site"}. Is the backend running?`);
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    // FastAPI sends errors as {"detail": "..."} or, for validation (422),
    // {"detail": [{"loc": [..., "ph"], "msg": "..."}]}.
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => `${d.loc?.at(-1)}: ${d.msg}`).join("; ")
      : detail || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  meta: () => request("/meta"),

  predictSoil: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/predict-soil", { method: "POST", body: form });
  },

  places: (query) => request(`/places?q=${encodeURIComponent(query)}`),

  weather: (lat, lon) => request(`/weather?lat=${lat}&lon=${lon}`),

  recommend: (body) =>
    request("/recommend-crop", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
};
