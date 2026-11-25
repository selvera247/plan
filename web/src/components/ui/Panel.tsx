import type { ReactNode } from "react";
import { clsx } from "clsx";

export type PanelProps = {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
  id?: string;
};

export function Panel({
  title,
  description,
  actions,
  children,
  className,
  as: Tag = "section",
  id,
}: PanelProps) {
  const headingId = id ? `${id}-title` : undefined;
  return (
    <Tag
      className={clsx("gf-panel", "gf-rise", className)}
      id={id}
      aria-labelledby={title && headingId ? headingId : undefined}
    >
      {(title || actions) && (
        <header className="gf-panel__header">
          <div>
            {title ? (
              <h2 className="gf-panel__title" id={headingId}>
                {title}
              </h2>
            ) : null}
            {description ? (
              <p className="gf-panel__desc">{description}</p>
            ) : null}
          </div>
          {actions}
        </header>
      )}
      {children}
    </Tag>
  );
}
