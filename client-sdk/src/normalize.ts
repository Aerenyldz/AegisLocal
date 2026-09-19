import type { MousePoint } from "./collectors/mouse.js";

/** Scale trajectory into unit box and re-base timestamps to t0=0. */
export function normalizeTrajectory(points: MousePoint[]): MousePoint[] {
  if (points.length === 0) return [];

  const xs = points.map((p) => p.x);
  const ys = points.map((p) => p.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const dx = Math.max(maxX - minX, 1);
  const dy = Math.max(maxY - minY, 1);
  const t0 = points[0].t;

  return points.map((p) => ({
    ...p,
    x: (p.x - minX) / dx,
    y: (p.y - minY) / dy,
    t: p.t - t0,
  }));
}
