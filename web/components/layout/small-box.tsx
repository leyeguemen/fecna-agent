import { SmallBox as AdminLTESmallBox } from "@adminlte/react";

/**
 * Small box oficial de AdminLTE 4.
 */
type SmallBoxColor = "primary" | "info" | "success" | "warning" | "danger";

export function SmallBox({
  value,
  label,
  color = "info",
  icon,
}: {
  value: string;
  label: string;
  color?: SmallBoxColor;
  icon?: React.ReactNode;
}) {
  return (
    <div className="[&_.small-box]:mb-0">
      <AdminLTESmallBox
        title={value}
        text={label}
        theme={color}
        icon={
          icon ? (
            <span
              aria-hidden="true"
              className="small-box-icon pointer-events-none select-none"
            >
              {icon}
            </span>
          ) : undefined
        }
      />
    </div>
  );
}
