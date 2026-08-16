import { describe, expect, it } from "vitest";
import {
  formatDuration,
  formatMoney,
  formatSignedMoney,
  hmToMinuteOfDay,
  kindEmoji,
  minuteOfDayToHM,
  parseMoneyToCents,
} from "../utils/format";

describe("formatMoney", () => {
  it("formats cents as dollars", () => {
    expect(formatMoney(0)).toBe("$0.00");
    expect(formatMoney(5)).toBe("$0.05");
    expect(formatMoney(1234)).toBe("$12.34");
    expect(formatMoney(100000)).toBe("$1,000.00");
  });
  it("handles negatives and symbols", () => {
    expect(formatMoney(-250)).toBe("-$2.50");
    expect(formatMoney(100, "HK$")).toBe("HK$1.00");
  });
});

describe("parseMoneyToCents", () => {
  it("parses dollars to cents", () => {
    expect(parseMoneyToCents("20")).toBe(2000);
    expect(parseMoneyToCents("$12.50")).toBe(1250);
    expect(parseMoneyToCents("0.99")).toBe(99);
  });
  it("rejects garbage and zero", () => {
    expect(parseMoneyToCents("abc")).toBeNull();
    expect(parseMoneyToCents("1.234")).toBeNull();
    expect(parseMoneyToCents("0")).toBeNull();
    expect(parseMoneyToCents("-5")).toBeNull();
  });
});

describe("formatDuration", () => {
  it("formats seconds as human durations", () => {
    expect(formatDuration(45)).toBe("0m");
    expect(formatDuration(600)).toBe("10m");
    expect(formatDuration(7500)).toBe("2h 05m");
  });
});

describe("formatSignedMoney", () => {
  it("adds plus for gains", () => {
    expect(formatSignedMoney(55)).toBe("+$0.55");
    expect(formatSignedMoney(-55)).toBe("-$0.55");
  });
});

describe("time-of-day helpers", () => {
  it("round trips", () => {
    expect(minuteOfDayToHM(0)).toBe("00:00");
    expect(minuteOfDayToHM(1190)).toBe("19:50");
    expect(hmToMinuteOfDay("19:50")).toBe(1190);
    expect(hmToMinuteOfDay("9:05")).toBe(545);
  });
  it("rejects bad input", () => {
    expect(hmToMinuteOfDay("25:00")).toBeNull();
    expect(hmToMinuteOfDay("nope")).toBeNull();
  });
});

describe("kindEmoji", () => {
  it("maps transaction kinds", () => {
    expect(kindEmoji("deposit")).toBe("💰");
    expect(kindEmoji("interest")).toBe("🌱");
    expect(kindEmoji("borrow")).toBe("🚀");
    expect(kindEmoji("mystery")).toBe("•");
  });
});
