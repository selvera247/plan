import {
  type ButtonHTMLAttributes,
  type ReactNode,
  forwardRef,
} from "react";
import { clsx } from "clsx";
import { Spinner } from "./Spinner";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  block?: boolean;
  /** Soft wrap for prompt chips / long labels on narrow screens */
  chip?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = "primary",
      size = "md",
      loading = false,
      block = false,
      chip = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      className,
      type = "button",
      ...rest
    },
    ref,
  ) {
    const isDisabled = disabled || loading;
    return (
      <button
        ref={ref}
        type={type}
        className={clsx(
          "gf-btn",
          `gf-btn--${variant}`,
          size !== "md" && `gf-btn--${size}`,
          block && "gf-btn--block",
          chip && "gf-btn--chip",
          className,
        )}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        aria-disabled={isDisabled || undefined}
        {...rest}
      >
        {loading ? <Spinner label="Working" /> : leftIcon}
        <span>{children}</span>
        {!loading && rightIcon}
      </button>
    );
  },
);
