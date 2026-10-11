import am from "./am.json";
import en from "./en.json";

function keys(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === "object" && v !== null ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe("localization files", () => {
  it("am.json and en.json define exactly the same keys", () => {
    expect(keys(am).sort()).toEqual(keys(en).sort());
  });
  it("no translation value is empty", () => {
    const empty = (o: Record<string, unknown>): boolean =>
      Object.values(o).some((v) => (typeof v === "object" && v ? empty(v as Record<string, unknown>) : v === ""));
    expect(empty(am)).toBe(false);
    expect(empty(en)).toBe(false);
  });
});
