/** Normalized mouse sample sent to AegisLocal API. */
export interface MousePoint {
  x: number;
  y: number;
  t: number;
  vx: number;
  vy: number;
  ax: number;
  ay: number;
}

export interface MouseCollectorOptions {
  /** Max buffered points before oldest are dropped. */
  maxPoints?: number;
  /** Ignore moves closer than this many ms. */
  minIntervalMs?: number;
  target?: Window | Document | HTMLElement;
}

/**
 * Collect pointer trajectory with velocity & acceleration.
 * Coordinates are viewport-relative; timestamps use performance.now().
 */
export class MouseCollector {
  private points: MousePoint[] = [];
  private readonly maxPoints: number;
  private readonly minIntervalMs: number;
  private readonly target: Window | Document | HTMLElement;
  private last: MousePoint | null = null;
  private listening = false;
  private readonly onMove: (ev: PointerEvent) => void;

  constructor(opts: MouseCollectorOptions = {}) {
    this.maxPoints = opts.maxPoints ?? 512;
    this.minIntervalMs = opts.minIntervalMs ?? 8;
    this.target = opts.target ?? window;
    this.onMove = (ev: PointerEvent) => this.handleMove(ev);
  }

  start(): void {
    if (this.listening) return;
    this.target.addEventListener("pointermove", this.onMove as EventListener, {
      passive: true,
    });
    this.listening = true;
  }

  stop(): void {
    if (!this.listening) return;
    this.target.removeEventListener("pointermove", this.onMove as EventListener);
    this.listening = false;
  }

  clear(): void {
    this.points = [];
    this.last = null;
  }

  snapshot(): MousePoint[] {
    return this.points.map((p) => ({ ...p }));
  }

  private handleMove(ev: PointerEvent): void {
    const t = performance.now();
    const x = ev.clientX;
    const y = ev.clientY;

    if (this.last && t - this.last.t < this.minIntervalMs) {
      return;
    }

    let vx = 0;
    let vy = 0;
    let ax = 0;
    let ay = 0;

    if (this.last) {
      const dt = Math.max((t - this.last.t) / 1000, 1e-6);
      vx = (x - this.last.x) / dt;
      vy = (y - this.last.y) / dt;
      ax = (vx - this.last.vx) / dt;
      ay = (vy - this.last.vy) / dt;
    }

    const point: MousePoint = { x, y, t, vx, vy, ax, ay };
    this.points.push(point);
    if (this.points.length > this.maxPoints) {
      this.points.shift();
    }
    this.last = point;
  }
}
