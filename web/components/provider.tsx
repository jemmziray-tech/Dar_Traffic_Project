"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { HistoryObservation, Observation, readHistory, readLive, ROADS } from "@/lib/traffic";

type Data = {
  live: Observation[];
  history: HistoryObservation[];
  loading: boolean;
  historyLoading: boolean;
  error: string | null;
  historyError: string | null;
  now: number;
  saved: string[];
  refresh: () => Promise<void>;
  loadHistory: (force?: boolean) => Promise<void>;
  toggleSaved: (id: string) => void;
};
const Context = createContext<Data | null>(null);
export function TrafficProvider({ children }: { children: React.ReactNode }) {
  const [live, setLive] = useState<Observation[]>([]),
    [history, setHistory] = useState<HistoryObservation[]>([]);
  const [loading, setLoading] = useState(false),
    [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null),
    [historyError, setHistoryError] = useState<string | null>(null);
  const [now, setNow] = useState(0),
    [saved, setSaved] = useState<string[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const fetchLive = useCallback(async () => {
    setLoading(true);
    try {
      setLive(await readLive());
      setError(null);
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "We could not refresh the traffic feed. Please try again.",
      );
    } finally {
      setLoading(false);
      setNow(Date.now());
    }
  }, []);
  const loadHistory = useCallback(async (force = false) => {
    setHistoryLoading(true);
    try {
      setHistory(await readHistory(force));
      setHistoryError(null);
    } catch {
      setHistoryError(
        "We could not load the recorded history. Please try again.",
      );
    } finally {
      setHistoryLoading(false);
    }
  }, []);
  useEffect(() => {
    setNow(Date.now());
    try {
      const value = JSON.parse(
        localStorage.getItem("dar-traffic-saved") ?? "[]",
      );
      if (Array.isArray(value))
        setSaved(value.filter((id): id is string => ROADS.some(road => road.id === id)));
    } catch {
      /* Storage can be unavailable in private browsing. */
    }
    setStorageReady(true);
    const timer = setInterval(() => {
      setNow(Date.now());
    }, 60000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (!storageReady) return;
    try {
      localStorage.setItem("dar-traffic-saved", JSON.stringify(saved));
    } catch {
      /* Saving is optional; reading traffic still works. */
    }
  }, [saved, storageReady]);
  const toggleSaved = useCallback(
    (id: string) =>
      setSaved((previous) => {
        return previous.includes(id)
          ? previous.filter((value) => value !== id)
          : [...previous, id];
      }),
    [],
  );
  return (
    <Context.Provider
      value={{
        live,
        history,
        loading,
        historyLoading,
        error,
        historyError,
        now,
        saved,
        refresh: fetchLive,
        loadHistory,
        toggleSaved,
      }}
    >
      {children}
    </Context.Provider>
  );
}
export function useTraffic() {
  const context = useContext(Context);
  if (!context) throw new Error("Traffic provider missing");
  return context;
}
