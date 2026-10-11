import { useState, useEffect } from "react";

interface TimeLeft { days: number; hours: number; minutes: number; seconds: number; expired: boolean; }

export function useCountdown(target: string | null | undefined): TimeLeft {
  const calc = (): TimeLeft => {
    if (!target) return { days: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
    const diff = new Date(target).getTime() - Date.now();
    if (diff <= 0) return { days: 0, hours: 0, minutes: 0, seconds: 0, expired: true };
    const s = Math.floor(diff / 1000);
    return {
      days:    Math.floor(s / 86400),
      hours:   Math.floor((s % 86400) / 3600),
      minutes: Math.floor((s % 3600) / 60),
      seconds: s % 60,
      expired: false,
    };
  };

  const [timeLeft, setTimeLeft] = useState<TimeLeft>(calc);

  useEffect(() => {
    if (!target) return;
    const id = setInterval(() => setTimeLeft(calc()), 1000);
    return () => clearInterval(id);
  }, [target]); // eslint-disable-line react-hooks/exhaustive-deps

  return timeLeft;
}
