import type { ReactNode } from "react";
import { clsx } from "clsx";

export type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
};

export function EmptyState({
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx("gf-empty", className)} role="status">
      <h3 className="gf-empty__title">{title}</h3>
      {description ? <p className="gf-empty__body">{description}</p> : null}
      {action ? <div style={{ marginTop: "1rem" }}>{action}</div> : null}
    </div>
  );
}
