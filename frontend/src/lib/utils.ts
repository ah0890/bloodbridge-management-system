import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const numberFmt = new Intl.NumberFormat("en-PK");
export const fmtNumber = (n: number | null | undefined) => (n == null ? "—" : numberFmt.format(n));

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function fmtDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  return d.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function fmtRelative(value: string | null | undefined): string {
  if (!value) return "—";
  const diff = (Date.now() - new Date(value).getTime()) / 1000;
  const abs = Math.abs(diff);
  const suffix = diff >= 0 ? "ago" : "from now";
  if (abs < 60) return "just now";
  if (abs < 3600) return `${Math.round(abs / 60)} min ${suffix}`;
  if (abs < 86400) return `${Math.round(abs / 3600)} h ${suffix}`;
  if (abs < 86400 * 30) return `${Math.round(abs / 86400)} d ${suffix}`;
  return fmtDate(value);
}

export const humanize = (s: string | null | undefined) =>
  s ? s.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "—";
