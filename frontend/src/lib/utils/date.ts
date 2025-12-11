import type { ExpiryValues } from "$lib/types";
import { add, format, formatDistance, parseISO } from "date-fns";

export function convertExpiryValueToDate(value: ExpiryValues): string | null {
  const now = new Date();
  let expiryDate: Date;

  switch (value) {
    case "5m":
      expiryDate = add(now, { minutes: 5 });
      break;
    case "15m":
      expiryDate = add(now, { minutes: 15 });
      break;
    case "30m":
      expiryDate = add(now, { minutes: 30 });
      break;
    case "1h":
      expiryDate = add(now, { hours: 1 });
      break;
    case "3h":
      expiryDate = add(now, { hours: 3 });
      break;
    case "1d":
      expiryDate = add(now, { days: 1 });
      break;
    case "never":
      return null;
    default:
      return null;
  }

  return format(expiryDate, "yyyy-MM-dd HH:mm:ss");
}

export function relativeDate(date: string | Date) {
  let targetDate: Date;
  if (typeof date === "string") {
    const utcString = date.endsWith("Z") ? date : date + "Z";

    targetDate = parseISO(utcString);
  } else {
    targetDate = date;
  }
  const now = new Date();
  return formatDistance(targetDate, now, {
    addSuffix: true,
  });
}
