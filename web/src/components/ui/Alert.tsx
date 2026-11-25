import type { ReactNode } from "react";
import { clsx } from "clsx";
import { Button } from "./Button";

export type AlertTone = "info" | "success" | "warning" | "error";

export type AlertProps = {
  tone?: AlertTone;
  title: string;
  children?: ReactNode;
  onDismiss?: () => void;
  className?: string;
};

const ICONS: Record<AlertTone, ReactNode> = {
  info: (
    <svg className="gf-alert__icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8v.01M12 12v4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  success: (
    <svg className="gf-alert__icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M8 12.5l2.5 2.5L16 9" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  warning: (
    <svg className="gf-alert__icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 3l10 18H2L12 3z" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M12 10v4M12 17v.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
  error: (
    <svg className="gf-alert__icon" viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2" />
      <path d="M15 9l-6 6M9 9l6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  ),
};

export function Alert({
  tone = "info",
  title,
  children,
  onDismiss,
  className,
}: AlertProps) {
  const role = tone === "error" || tone === "warning" ? "alert" : "status";
  return (
    <div
      className={clsx("gf-alert", `gf-alert--${tone}`, className)}
      role={role}
      aria-live={tone === "error" ? "assertive" : "polite"}
    >
      {ICONS[tone]}
      <div>
        <p className="gf-alert__title">{title}</p>
        {children ? <div className="gf-alert__body">{children}</div> : null}
      </div>
      {onDismiss ? (
        <Button
          variant="ghost"
          size="sm"
          onClick={onDismiss}
          aria-label="Dismiss"
        >
          ×
        </Button>
      ) : (
        <span />
      )}
    </div>
  );
}
