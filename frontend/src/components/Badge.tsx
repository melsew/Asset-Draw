type BadgeVariant = "green" | "blue" | "gold" | "gray" | "red" | "navy";

interface BadgeProps {
  variant?: BadgeVariant;
  children: React.ReactNode;
  className?: string;
}

export function Badge({ variant = "gray", children, className = "" }: BadgeProps) {
  return (
    <span className={`ad-badge ad-badge-${variant} ${className}`}>
      {children}
    </span>
  );
}

export function entryModeBadge(mode: string): BadgeVariant {
  if (mode === "FREE") return "green";
  if (mode === "PROMOTIONAL") return "blue";
  return "gray";
}

export function statusBadge(status: string): BadgeVariant {
  if (status === "ACTIVE")          return "green";
  if (status === "SCHEDULED")       return "blue";
  if (status === "DRAWING")         return "gold";
  if (status === "DRAW_COMPLETED")  return "navy";
  if (status === "COMPLETED")       return "navy";
  if (status === "SUSPENDED")       return "red";
  if (status === "CANCELLED")       return "red";
  return "gray";
}
