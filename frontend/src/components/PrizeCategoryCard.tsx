import type { LucideIcon } from "lucide-react";

interface PrizeCategoryCardProps {
  icon?: LucideIcon;
  art?: string;
  title: string;
  onClick?: () => void;
}

export function PrizeCategoryCard({ icon: Icon, art, title, onClick }: PrizeCategoryCardProps) {
  return (
    <button type="button" className="ad-prize-card" onClick={onClick}>
      {art ? (
        <div className="ad-prize-card-art" aria-hidden="true">
          <img src={art} alt="" />
        </div>
      ) : Icon ? (
        <Icon size={28} />
      ) : null}
      <span>{title}</span>
    </button>
  );
}
