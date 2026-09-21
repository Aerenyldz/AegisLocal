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
  /** Policy selected by the host application for analysis requests. */
  policy?: AegisPolicy;
  /** Login form selector or element used for SDK lifecycle binding. */
  form?: string | HTMLFormElement;
  /** Host-owned challenge container; the SDK never writes credentials here. */
  challengeContainer?: string | HTMLElement;
  /** Keep collecting and report decisions without enforcing them. */
  mode?: "live" | "shadow";
}

export type AegisPolicy =
  | "default"
  | "login_protection"
  | "high_assurance"
  | (string & {});

export interface AnalyzeResult {
  decision: "allow" | "soft_challenge" | "deny";
  risk_score: number;
  label: string;
  xai: Record<string, number>;
  reasons: string[];
  features: Record<string, number>;
  enforcement?: "allow" | "challenge" | "throttle" | "deny";
  policy?: string;
  mode?: "live" | "shadow";
  rate_limit_remaining?: number;
  model_version?: string;
}

/** Login preflight request fields sent to the gateway. */
interface LoginPreflightRequest {
  session_id: string;
  points: MousePoint[];
  webdriver: boolean;
  policy: AegisPolicy;
  mode: "live" | "shadow";
}

/** Create a browser-local identifier without involving form data. */
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
  private readonly policy: AegisPolicy;
  private readonly mode: "live" | "shadow";
  private form: HTMLFormElement | null = null;
  private challengeContainer: HTMLElement | null = null;

  constructor(opts: AegisClientOptions) {
    this.sessionId = opts.sessionId ?? randomSessionId();
    this.policy = opts.policy ?? "default";
    this.mode = opts.mode ?? "live";
    this.transport = new AegisTransport({
      baseUrl: opts.baseUrl.replace(/\/$/, ""),
      sessionId: this.sessionId,
    });
    if (opts.form != null) {
      this.bindForm(opts.form);
    }
    if (opts.challengeContainer != null) {
      this.challengeContainer = this.resolveElement(
        opts.challengeContainer,
        "challenge container",
      );
    }
    if (opts.autoStart !== false) {
      this.start();
    }
  }

  /** Bind the SDK to a login form without reading or submitting its values. */
  bindForm(form: string | HTMLFormElement): void {
    this.form = this.resolveForm(form);
  }

  /** Return the currently bound form, if one was configured. */
  getBoundForm(): HTMLFormElement | null {
    return this.form;
  }

  /** Return the host-owned challenge container, if one was configured. */
  getChallengeContainer(): HTMLElement | null {
    return this.challengeContainer;
  }

  /** Remove the current form binding while leaving telemetry collection intact. */
  unbindForm(): void {
    this.form = null;
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
      policy: this.policy,
      mode: this.mode,
      pow,
    });
  }

  /**
   * Request a login decision without inspecting the bound form or its values.
   *
   * The login endpoint accepts an empty trajectory for keyboard, touch, and
   * screen-reader flows. Username and password are intentionally absent from
   * this request body.
   */
  async preflight(endpoint = "login"): Promise<AnalyzeResult> {
    if (endpoint !== "login") {
      throw new Error(`Unsupported preflight endpoint: ${endpoint}`);
    }

    const fp = await this.fingerprint();
    const body: LoginPreflightRequest = {
      session_id: this.sessionId,
      points: this.getNormalizedMouse(),
      webdriver: fp.webdriver,
      policy: this.policy,
      mode: this.mode,
    };
    return this.transport.postJson<AnalyzeResult>("/v1/analyze/login", body);
  }

  /** Resolve a configured form selector or element. */
  private resolveForm(form: string | HTMLFormElement): HTMLFormElement {
    const element = this.resolveElement(form, "login form");
    if (!(element instanceof HTMLFormElement)) {
      throw new TypeError("The configured form must resolve to an HTMLFormElement");
    }
    return element;
  }

  /** Resolve a selector or element without reading any form values. */
  private resolveElement(
    value: string | HTMLElement,
    description: string,
  ): HTMLElement {
    const element =
      typeof value === "string"
        ? document.querySelector<HTMLElement>(value)
        : value;
    if (!element) {
      throw new Error(`Unable to find ${description}: ${String(value)}`);
    }
    return element;
  }
}

export { MouseCollector, normalizeTrajectory, collectFingerprint, solveChallenge };
export type { MousePoint, FingerprintSignals, PowChallenge };
