import { solvePowJs, type JsPowResult } from "./jsFallback.js";

export interface PowChallenge {
  challenge_id: string;
  nonce_prefix: string;
  difficulty: number;
}

export type PowSolver = "wasm" | "js";

/**
 * Prefer WASM module when loaded; otherwise WebCrypto JS loop.
 * WASM glue is produced by `wasm-pack` under pow-wasm/pkg (optional at MVP).
 */
export async function solveChallenge(
  challenge: PowChallenge,
  wasmModule?: {
    solve: (nonce_prefix: string, challenge_id: string, difficulty: number) => {
      counter: number;
      digest: string;
    };
  }
): Promise<JsPowResult & { solver: PowSolver }> {
  if (wasmModule?.solve) {
    const t0 = performance.now();
    const r = wasmModule.solve(
      challenge.nonce_prefix,
      challenge.challenge_id,
      challenge.difficulty
    );
    return {
      counter: r.counter,
      digest: r.digest,
      elapsedMs: performance.now() - t0,
      solver: "wasm",
    };
  }
  const r = await solvePowJs(
    challenge.nonce_prefix,
    challenge.challenge_id,
    challenge.difficulty
  );
  return { ...r, solver: "js" };
}
