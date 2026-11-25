import {
  type SelectHTMLAttributes,
  type ReactNode,
  forwardRef,
  useId,
} from "react";
import { clsx } from "clsx";

export type SelectOption = {
  value: string;
  label: string;
  disabled?: boolean;
};

export type SelectFieldProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  options: SelectOption[];
  hint?: ReactNode;
  error?: string;
  placeholder?: string;
};

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  function SelectField(
    {
      label,
      options,
      hint,
      error,
      placeholder,
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
        <label htmlFor={inputId} className="gf-field__label">
          {label}
          {required ? <span aria-hidden="true"> *</span> : null}
        </label>
        <select
          ref={ref}
          id={inputId}
          className="gf-select"
          disabled={disabled}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          {...rest}
        >
          {placeholder ? (
            <option value="" disabled>
              {placeholder}
            </option>
          ) : null}
          {options.map((opt) => (
            <option
              key={opt.value}
              value={opt.value}
              disabled={opt.disabled}
            >
              {opt.label}
            </option>
          ))}
        </select>
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
