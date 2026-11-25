import {
  type TextareaHTMLAttributes,
  type ReactNode,
  forwardRef,
  useId,
} from "react";
import { clsx } from "clsx";

export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  hint?: ReactNode;
  error?: string;
  hideLabel?: boolean;
};

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  function TextArea(
    {
      label,
      hint,
      error,
      hideLabel = false,
      id,
      className,
      disabled,
      required,
      ...rest
    },
    ref,
  ) {
    const autoId = useId();
    const inputId = id ?? autoId;
    const hintId = `${inputId}-hint`;
    const errorId = `${inputId}-error`;
    const describedBy = [
      hint ? hintId : null,
      error ? errorId : null,
    ]
      .filter(Boolean)
      .join(" ") || undefined;

    return (
      <div className={clsx("gf-field", className)}>
        <label
          htmlFor={inputId}
          className={clsx("gf-field__label", hideLabel && "gf-vh")}
        >
          {label}
          {required ? <span aria-hidden="true"> *</span> : null}
        </label>
        <textarea
          ref={ref}
          id={inputId}
          className="gf-textarea"
          disabled={disabled}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...rest}
        />
        {hint && !error ? (
          <span id={hintId} className="gf-field__hint">
            {hint}
          </span>
        ) : null}
        {error ? (
          <span id={errorId} className="gf-field__error" role="alert">
            {error}
          </span>
        ) : null}
      </div>
    );
  },
);
