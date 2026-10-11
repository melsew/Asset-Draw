interface SpinnerProps {
  size?: "sm" | "md" | "lg";
  variant?: "navy" | "gold" | "white";
  center?: boolean;
}

export function Spinner({ size = "md", variant = "navy", center = false }: SpinnerProps) {
  const cls = [
    "ad-spinner",
    size === "sm" ? "ad-spinner-sm" : size === "lg" ? "ad-spinner-lg" : "",
    variant === "gold" ? "ad-spinner-gold" : variant === "white" ? "ad-spinner-white" : "",
  ].filter(Boolean).join(" ");

  if (center) return <div className="ad-center-spinner"><span className={cls} aria-label="Loading" /></div>;
  return <span className={cls} aria-label="Loading" />;
}
