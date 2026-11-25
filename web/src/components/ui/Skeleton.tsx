import { clsx } from "clsx";

export type SkeletonProps = {
  width?: string | number;
  height?: string | number;
  className?: string;
  /** Accessible label announced while content loads */
  label?: string;
};

export function Skeleton({
  width = "100%",
  height = "1rem",
  className,
  label = "Loading content",
}: SkeletonProps) {
  return (
    <span
      className={clsx("gf-skeleton", className)}
      style={{ width, height }}
      role="status"
      aria-busy="true"
      aria-label={label}
    />
  );
}
