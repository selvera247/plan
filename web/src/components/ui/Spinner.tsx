import { clsx } from "clsx";
import { VisuallyHidden } from "./VisuallyHidden";

export type SpinnerProps = {
  size?: "sm" | "lg";
  label?: string;
  className?: string;
};

export function Spinner({
  size = "sm",
  label = "Loading",
  className,
}: SpinnerProps) {
  return (
    <span
      className={clsx("gf-spinner", size === "lg" && "gf-spinner--lg", className)}
      role="status"
      aria-live="polite"
    >
      <VisuallyHidden>{label}</VisuallyHidden>
    </span>
  );
}
