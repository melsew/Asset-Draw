// Asset-Draw standalone verifier, protocol asset-draw/v1 (browser + Node >= 20, no dependencies).
// Port of verifier/verify_draw.py (which was written from the protocol spec). Both implementations
// must agree on every vector in tests/vectors/draw_v1.json - enforced by backend/tests/test_draw_verifiers.py.
// Contract used by cli.mjs and the public verification page: verifyPackage(pkg) -> { ok, checks[] }.
const enc = new TextEncoder();
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const SOURCE_RE = /^[a-z0-9][a-z0-9:_./-]{0,127}$/;
const VALUE_RE = /^(?:[0-9a-f]{2})+$/;
const U64 = 1n << 64n;
const MAX_REJECTION_ROUNDS = 256;

const toHex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
const concat = (...parts) => {
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
};
const sha256Hex = async (bytes) => toHex(await crypto.subtle.digest("SHA-256", bytes));
const isInt = (v) => typeof v === "number" && Number.isSafeInteger(v);

// Mirrors Python's bytes.fromhex for the cases that matter here: even-length hex digits.
function parseHex(s) {
  if (typeof s !== "string" || s.length % 2 !== 0 || !/^[0-9a-fA-F]*$/.test(s)) throw new TypeError("invalid hex");
  return Uint8Array.from(s.match(/../g) ?? [], (h) => parseInt(h, 16));
}

async function hmacSha256(keyBytes, data) {
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return new Uint8Array(await crypto.subtle.sign("HMAC", key, data));
}

async function unbiasedIndex(seed, message, n) {
  const nBig = BigInt(n);
  const limit = (U64 / nBig) * nBig;
  for (let counter = 0; counter < MAX_REJECTION_ROUNDS; counter++) {
    const ctr = new Uint8Array(4);
    new DataView(ctr.buffer).setUint32(0, counter, false);
    const block = await hmacSha256(seed, concat(message, Uint8Array.of(0), ctr));
    let x = 0n;
    for (let i = 0; i < 8; i++) x = (x << 8n) | BigInt(block[i]);
    if (x < limit) return Number(x % nBig);
  }
  return null;
}

// Never throws on bad evidence. Returns { ok, checks: [{ name, ok, detail }] }.
export async function verifyPackage(pkg) {
  const checks = [];
  const check = (name, ok, detail = "") => { checks.push({ name, ok: Boolean(ok), detail }); return Boolean(ok); };
  const fail = () => ({ ok: false, checks });

  let cid, did, entries, ent, seed, prizes;
  try {
    cid = pkg.campaign_id; did = pkg.draw_id; entries = pkg.entry_numbers; ent = pkg.entropy;
    prizes = pkg.prizes;
    seed = parseHex(pkg.seed);
    if ([cid, did, entries, ent, pkg.seed, prizes].some((v) => v === undefined || v === null)) throw new TypeError("missing field");
  } catch (e) {
    check("package is well-formed", false, `${e.name}: ${e.message}`);
    return fail();
  }

  if (!check("protocol version", pkg.protocol === "asset-draw/v1", String(pkg.protocol))) return fail();
  if (!check("identifiers are canonical UUIDs", UUID_RE.test(String(cid)) && UUID_RE.test(String(did)))) return fail();

  const ascending = Array.isArray(entries) && entries.length > 0 && entries.every(isInt)
    && entries.every((n, i) => n > (i === 0 ? 0 : entries[i - 1]));
  if (!check("entry numbers are positive, strictly ascending", ascending)) return fail();
  if (!check("seed is 32 bytes", seed.length === 32)) return fail();

  const entOk = typeof ent === "object" && ent !== null
    && SOURCE_RE.test(String(ent.source ?? "")) && isInt(ent.round) && ent.round >= 1
    && VALUE_RE.test(String(ent.value ?? ""));
  if (!check("entropy fields are valid", entOk)) return fail();

  const poolText = `asset-draw/pool/v1\n${cid}\n${entries.length}\n${entries.join(",")}`;
  const ph = await sha256Hex(enc.encode(poolText));
  check("pool hash matches the published entry list", ph === pkg.pool_hash);
  const commit = await sha256Hex(concat(enc.encode("asset-draw/seed/v1\n"), seed));
  check("seed matches the commitment published before the draw", commit === pkg.seed_commitment);

  const prizeList = Array.isArray(prizes) ? prizes : [];
  const indexesOk = Array.isArray(prizes) && prizes.every((p, i) => p !== null && typeof p === "object" && p.prize_index === i);
  if (!check("prize indexes are 0..k-1 in order", indexesOk)) return fail();
  if (!check("not more prizes than entries", prizeList.length > 0 && prizeList.length <= entries.length)) return fail();

  const remaining = [...entries];
  for (let k = 0; k < prizeList.length; k++) {
    const p = prizeList[k];
    const msg = enc.encode(
      `asset-draw/v1\ncampaign_id=${cid}\ndraw_id=${did}\npool_hash=${ph}\n`
      + `entropy_source=${ent.source}\nentropy_round=${ent.round}\nentropy_value=${ent.value}\nprize_index=${k}`,
    );
    const n = remaining.length;
    const idx = await unbiasedIndex(seed, msg, n);
    if (idx === null) { check(`prize ${k}: index derivation`, false, "rejection sampling exhausted"); return fail(); }
    const winner = remaining[idx];
    check(`prize ${k}: pool size`, p.remaining_count === n, `expected ${n}`);
    check(`prize ${k}: winner index`, p.winner_index === idx, `expected ${idx}`);
    check(`prize ${k}: winning entry number`, p.winning_entry_number === winner, `expected ${winner}`);
    remaining.splice(idx, 1);
  }
  return { ok: checks.every((c) => c.ok), checks };
}
