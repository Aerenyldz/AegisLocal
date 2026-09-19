import { MouseCollector, type MousePoint } from "./collectors/mouse.js";
import { KeyboardCollector } from "./collectors/keyboard.js";
import { collectFingerprint, type FingerprintSignals } from "./collectors/fingerprint.js";
import { normalizeTrajectory } from "./normalize.js";
import { AegisTransport } from "./transport.js";
import { solveChallenge, type PowChallenge } from "./pow/client.js";

export interface AegisClientOptions {
  baseUrl: string;
  sessionId?: string;
  autoStart?: boolean;
}

export interface AnalyzeResult {
  decision: "allow" | "soft_challenge" | "deny";
  risk_score: number;
  label: string;
  xai: Record<string, number>;
  reasons: string[];
  features: Record<string, number>;
}

function randomSessionId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export class AegisClient {
  readonly sessionId: string;
  private readonly transport: AegisTransport;
  private readonly mouse = new MouseCollector();
  private readonly keyboard = new KeyboardCollector();

  constructor(opts: AegisClientOptions) {
    this.sessionId = opts.sessionId ?? randomSessionId();
    this.transport = new AegisTransport({
      baseUrl: opts.baseUrl.replace(/\/$/, ""),
      sessionId: this.sessionId,
    });
    if (opts.autoStart !== false) {
      this.start();
    }
  }

  start(): void {
    this.mouse.start();
    this.keyboard.start();
  }

  stop(): void {
    this.mouse.stop();
    this.keyboard.stop();
  }

  getNormalizedMouse(): MousePoint[] {
    return normalizeTrajectory(this.mouse.snapshot());
  }

  async fingerprint(): Promise<FingerprintSignals> {
    return collectFingerprint();
  }

  async requestPowChallenge(difficulty?: number): Promise<PowChallenge> {
    const q = difficulty != null ? `?difficulty=${difficulty}` : "";
    return this.transport.postJson<PowChallenge>(`/v1/pow/challenge${q}`, {});
  }

  async analyze(includePow = true): Promise<AnalyzeResult> {
    const points = this.getNormalizedMouse();
    if (points.length < 8) {
      throw new Error("Need at least 8 mouse points — move the pointer first");
    }

    const fp = await this.fingerprint();
    let pow: { challenge_id: string; counter: number; digest: string } | undefined;

    if (includePow) {
      const challenge = await this.requestPowChallenge();
      const proof = await solveChallenge(challenge);
      pow = {
        challenge_id: challenge.challenge_id,
        counter: proof.counter,
        digest: proof.digest,
      };
    }

    return this.transport.postJson<AnalyzeResult>("/v1/analyze/mouse", {
      session_id: this.sessionId,
      points,
      webdriver: fp.webdriver,
      fingerprint: fp,
      pow,
    });
  }
}

export { MouseCollector, normalizeTrajectory, collectFingerprint, solveChallenge };
export type { MousePoint, FingerprintSignals, PowChallenge };
