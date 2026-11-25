import type { ReactNode } from "react";

/** Hide visually but keep available to assistive tech. */
export function VisuallyHidden({ children }: { children: ReactNode }) {
  return <span className="gf-vh">{children}</span>;
}
