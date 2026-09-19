export interface KeyEventSample {
  type: "down" | "up";
  code: string;
  t: number;
}

/** Lightweight keystroke rhythm collector (no key values / PII). */
export class KeyboardCollector {
  private samples: KeyEventSample[] = [];
  private readonly maxSamples: number;
  private listening = false;

  private readonly onDown: (ev: KeyboardEvent) => void;
  private readonly onUp: (ev: KeyboardEvent) => void;

  constructor(maxSamples = 256) {
    this.maxSamples = maxSamples;
    this.onDown = (ev) => this.push("down", ev.code);
    this.onUp = (ev) => this.push("up", ev.code);
  }

  start(): void {
    if (this.listening) return;
    window.addEventListener("keydown", this.onDown, { passive: true });
    window.addEventListener("keyup", this.onUp, { passive: true });
    this.listening = true;
  }

  stop(): void {
    if (!this.listening) return;
    window.removeEventListener("keydown", this.onDown);
    window.removeEventListener("keyup", this.onUp);
    this.listening = false;
  }

  snapshot(): KeyEventSample[] {
    return this.samples.map((s) => ({ ...s }));
  }

  private push(type: "down" | "up", code: string): void {
    this.samples.push({ type, code, t: performance.now() });
    if (this.samples.length > this.maxSamples) this.samples.shift();
  }
}
