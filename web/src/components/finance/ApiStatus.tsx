import { useEffect, useState } from "react";
import { Badge } from "../ui";
import { checkHealth } from "../../lib/api";

export function ApiStatus() {
  const [status, setStatus] = useState<"checking" | "ok" | "down">("checking");
  const [label, setLabel] = useState("checking");

  useEffect(() => {
    const ac = new AbortController();
    let cancelled = false;

    async function ping() {
      const res = await checkHealth(ac.signal);
      if (cancelled) return;
      setStatus(res.ok ? "ok" : "down");
      setLabel(res.status);
    }

    ping();
    const id = window.setInterval(ping, 15000);
    return () => {
      cancelled = true;
      ac.abort();
      window.clearInterval(id);
    };
  }, []);

  const tone =
    status === "ok" ? "ok" : status === "down" ? "danger" : "neutral";

  return (
    <Badge tone={tone} title="API /health">
      API {label}
    </Badge>
  );
}
