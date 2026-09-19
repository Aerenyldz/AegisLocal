/** Pure JS SHA-256 PoW fallback when WASM is unavailable. */

async function sha256Hex(message: string): Promise<string> {
  const data = new TextEncoder().encode(message);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function meetsDifficulty(hex: string, bits: number): boolean {
  const fullBytes = Math.floor(bits / 8);
  const rem = bits % 8;
  for (let i = 0; i < fullBytes; i++) {
    if (hex.slice(i * 2, i * 2 + 2) !== "00") return false;
  }
  if (rem === 0) return true;
  const next = parseInt(hex.slice(fullBytes * 2, fullBytes * 2 + 2), 16);
  const mask = (0xff << (8 - rem)) & 0xff;
  return (next & mask) === 0;
}

export interface JsPowResult {
  counter: number;
  digest: string;
  elapsedMs: number;
}

export async function solvePowJs(
  noncePrefix: string,
  challengeId: string,
  difficulty: number,
  maxIterations = 5_000_000
): Promise<JsPowResult> {
  const t0 = performance.now();
  for (let counter = 0; counter < maxIterations; counter++) {
    const payload = `${noncePrefix}:${challengeId}:${counter}`;
    const digest = await sha256Hex(payload);
    if (meetsDifficulty(digest, difficulty)) {
      return { counter, digest, elapsedMs: performance.now() - t0 };
    }
  }
  throw new Error("PoW JS fallback exceeded maxIterations");
}
