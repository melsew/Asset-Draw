import { useTranslation } from "react-i18next";
import { useCountdown } from "../hooks/useCountdown";

interface CountdownProps {
  drawAt?: string | null;
  status?: string;
}

export function Countdown({ drawAt, status }: CountdownProps) {
  const { t } = useTranslation();
  const tl = useCountdown(drawAt);

  if (status === "DRAW_COMPLETED" || status === "COMPLETED") {
    return <span className="ad-badge ad-badge-navy" style={{ alignSelf: "flex-start" }}>{t("countdown.resultPublished")}</span>;
  }
  if (status === "DRAWING") {
    return <span className="ad-badge ad-badge-gold" style={{ alignSelf: "flex-start" }}>{t("countdown.inProgress")}</span>;
  }
  if (!drawAt) {
    return <span className="ad-text-soft ad-text-sm">{t("countdown.notScheduled")}</span>;
  }
  if (tl.expired) {
    return <span className="ad-text-soft ad-text-sm">{t("countdown.awaitingStatus")}</span>;
  }

  const units = [
    { val: tl.days,    key: "countdown.days" },
    { val: tl.hours,   key: "countdown.hours" },
    { val: tl.minutes, key: "countdown.minutes" },
    { val: tl.seconds, key: "countdown.seconds" },
  ];

  return (
    <div
      className="ad-countdown"
      aria-label={t("countdown.accessible", { ...tl })}
    >
      {units.map(({ val, key }, i) => (
        <>
          {i > 0 && <span className="ad-countdown-sep" aria-hidden="true">:</span>}
          <div className="ad-countdown-unit" key={key}>
            <span className="ad-countdown-num">{String(val).padStart(2, "0")}</span>
            <span className="ad-countdown-label">{t(key)}</span>
          </div>
        </>
      ))}
    </div>
  );
}
