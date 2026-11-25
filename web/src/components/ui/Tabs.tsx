import {
  type KeyboardEvent,
  type ReactNode,
  useId,
  useState,
} from "react";
import { clsx } from "clsx";

export type TabItem = {
  id: string;
  label: string;
  panel: ReactNode;
  disabled?: boolean;
};

export type TabsProps = {
  items: TabItem[];
  defaultTab?: string;
  label: string;
  className?: string;
  onChange?: (id: string) => void;
};

export function Tabs({
  items,
  defaultTab,
  label,
  className,
  onChange,
}: TabsProps) {
  const baseId = useId();
  const firstEnabled = items.find((t) => !t.disabled)?.id ?? items[0]?.id;
  const [active, setActive] = useState(defaultTab ?? firstEnabled);

  function select(id: string) {
    setActive(id);
    onChange?.(id);
  }

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const enabled = items.filter((t) => !t.disabled);
    const idx = enabled.findIndex((t) => t.id === active);
    if (idx < 0) return;
    let next = idx;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      next = (idx + 1) % enabled.length;
      e.preventDefault();
    } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      next = (idx - 1 + enabled.length) % enabled.length;
      e.preventDefault();
    } else if (e.key === "Home") {
      next = 0;
      e.preventDefault();
    } else if (e.key === "End") {
      next = enabled.length - 1;
      e.preventDefault();
    } else {
      return;
    }
    select(enabled[next].id);
    document.getElementById(`${baseId}-tab-${enabled[next].id}`)?.focus();
  }

  const current = items.find((t) => t.id === active) ?? items[0];

  return (
    <div className={className}>
      <div
        className="gf-tabs"
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
      >
        {items.map((tab) => {
          const selected = tab.id === active;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tab.id}`}
              className={clsx("gf-tab")}
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${tab.id}`}
              tabIndex={selected ? 0 : -1}
              disabled={tab.disabled}
              onClick={() => select(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      {current ? (
        <div
          role="tabpanel"
          id={`${baseId}-panel-${current.id}`}
          aria-labelledby={`${baseId}-tab-${current.id}`}
          className="gf-rise"
        >
          {current.panel}
        </div>
      ) : null}
    </div>
  );
}
