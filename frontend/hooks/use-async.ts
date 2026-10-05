"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api/client";

export interface AsyncState<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

interface Settled<T> {
  key: string;
  data: T | null;
  error: string | null;
}

/** Runs `fn` on mount and whenever `deps` change. Stale responses are ignored; previous data stays visible while reloading. */
export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [tick, setTick] = useState(0);
  const key = JSON.stringify([...deps, tick]);
  const [settled, setSettled] = useState<Settled<T>>({ key: "", data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    fn()
      .then((data) => !cancelled && setSettled({ key, data, error: null }))
      .catch((e: unknown) => {
        if (cancelled) return;
        const error = e instanceof ApiError ? e.message : "Something went wrong. Please try again.";
        setSettled((s) => ({ key, data: s.data, error }));
      });
    return () => {
      cancelled = true;
    };
    // `fn` is intentionally excluded: callers pass a fresh closure each render; `deps` drive refetching.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  const current = settled.key === key;
  return { data: settled.data, error: current ? settled.error : null, loading: !current, reload };
}
