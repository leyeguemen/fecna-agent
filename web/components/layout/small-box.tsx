import { cn } from "@/lib/utils";

/**
 * "Small box" de AdminLTE: caja de estadística con color de estado, número
 * grande y un icono fantasma a la derecha.
 */
const COLORS = {
  primary: "bg-primary text-primary-foreground",
  info: "bg-lte-info text-white",
  success: "bg-lte-success text-white",
  warning: "bg-lte-warning text-neutral-900",
  danger: "bg-lte-danger text-white",
} as const;

export function SmallBox({
  value,
  label,
  color = "info",
  icon,
}: {
  value: string;
  label: string;
  color?: keyof typeof COLORS;
  icon?: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-lg p-4 shadow-sm",
        COLORS[color],
      )}
    >
      <div className="text-3xl font-bold tracking-tight">{value}</div>
      <p className="mt-1 text-sm opacity-90">{label}</p>
      {icon && (
        <span
          aria-hidden="true"
          className="pointer-events-none absolute -right-1 -top-1 select-none text-6xl opacity-20"
        >
          {icon}
        </span>
      )}
    </div>
  );
}
