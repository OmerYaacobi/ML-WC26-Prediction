/* Shared fixture status helpers — trust API status from fixtures.json */
"use strict";

window.WC26FixtureHelpers = (() => {
  function parseKickoff(iso) {
    if (!iso) return null;
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  /** Use the status written by fetch_fixtures.py — do not re-guess from scores. */
  function effectiveStatus(f) {
    if (!f) return "pending";
    return f.status || "pending";
  }

  function isFinished(f) {
    return !!(f && f.status === "settled");
  }

  function isLive(f) {
    return !!(f && f.status === "live");
  }

  function isActive(f) {
    const s = effectiveStatus(f);
    return s === "pending" || s === "live";
  }

  function isBettableFixture(f) {
    if (!f || f.status !== "pending") return false;
    if (f.bettable === false) return false;
    const kick = parseKickoff(f.kickoff);
    if (kick && kick <= new Date()) return false;
    return true;
  }

  function statusLabel(f) {
    if (!f) return "";
    const status = effectiveStatus(f);
    if (status === "settled" && f.homeScore != null && f.awayScore != null) {
      return `${f.homeScore}–${f.awayScore} FT`;
    }
    if (status === "live") {
      if (f.homeScore != null && f.awayScore != null) {
        return `LIVE · ${f.homeScore}–${f.awayScore}`;
      }
      return "LIVE";
    }
    if (status === "cancelled") return "Cancelled";
    if (!f.kickoff) return "Awaiting schedule";
    return new Date(f.kickoff).toLocaleString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function sortActive(a, b) {
    if (a.status === "live" && b.status !== "live") return -1;
    if (b.status === "live" && a.status !== "live") return 1;
    return (a.kickoff || "").localeCompare(b.kickoff || "");
  }

  function sortFinished(a, b) {
    return (b.kickoff || "").localeCompare(a.kickoff || "");
  }

  return {
    parseKickoff,
    effectiveStatus,
    isFinished,
    isLive,
    isActive,
    isBettableFixture,
    statusLabel,
    sortActive,
    sortFinished,
  };
})();
