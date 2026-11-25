import type { ReactNode } from "react";
import { clsx } from "clsx";

export type BadgeTone = "neutral" | "ok" | "warn" | "danger" | "info";

export type BadgeProps = {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
  title?: string;
};

export function Badge({
  children,
  tone = "neutral",
  className,
  title,
}: BadgeProps) {
  return (
    <span
      className={clsx(
        "gf-badge",
        tone !== "neutral" && `gf-badge--${tone}`,
        className,
      )}
      title={title}
    >
      {children}
    </span>
  );
}
