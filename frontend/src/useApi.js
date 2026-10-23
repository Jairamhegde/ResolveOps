import { useEffect, useState } from "react";

// Runs `load()` (a function returning a promise) whenever `deps` change, and every `refreshMs` if given.
// Returns { data, error, loading, reload }. Old data stays on screen while new data loads.
export function useApi(load, deps, refreshMs = 0) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;

    function run() {
      setLoading(true);
      load()
        .then((result) => {
          if (cancelled) return;
          setData(result);
          setError("");
        })
        .catch((loadError) => {
          if (!cancelled) setError(loadError.message);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }

    run();
    const timer = refreshMs ? setInterval(() => !document.hidden && run(), refreshMs) : null;

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [...deps, attempt]);

  return { data, error, loading, reload: () => setAttempt((count) => count + 1) };
}
