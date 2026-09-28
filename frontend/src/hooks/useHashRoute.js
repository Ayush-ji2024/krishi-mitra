import { useEffect, useState } from "react";

// A tiny router using the part of the URL after "#" (e.g. /#/advisor).
// Why hash routing: it works on ANY static host (Vercel, Netlify, GitHub Pages)
// without extra server settings, and needs no extra library.
const read = () => window.location.hash.replace(/^#/, "") || "/";

export function useHashRoute() {
  const [path, setPath] = useState(read);

  useEffect(() => {
    const onChange = () => {
      setPath(read());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  return path;
}
