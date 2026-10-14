/**
 * web/src/formatters.js — Shared Formatting Utilities
 * Standardized numerical, currency, and time formatters for BTCognitive.
 */

function formatPrice(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return Number(val).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

function formatPct(val, decimals = 2, showSign = true) {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const num = Number(val);
  const sign = showSign && num > 0 ? "+" : "";
  return `${sign}${num.toFixed(decimals)}%`;
}

function formatBps(val, decimals = 1, showSign = true) {
  if (val === null || val === undefined || isNaN(val)) return "—";
  const num = Number(val);
  const sign = showSign && num > 0 ? "+" : "";
  return `${sign}${num.toFixed(decimals)} bps`;
}

function formatIsoTime(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, " UTC");
  } catch {
    return String(isoString);
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { formatPrice, formatPct, formatBps, formatIsoTime };
}
