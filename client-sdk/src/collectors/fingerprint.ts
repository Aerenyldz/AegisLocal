export interface FingerprintSignals {
  webdriver: boolean;
  language: string;
  platform: string;
  hardwareConcurrency: number;
  deviceMemory: number | null;
  maxTouchPoints: number;
  timezoneOffset: number;
  canvasHash: string;
  webglVendor: string | null;
  webglRenderer: string | null;
}

async function sha256Short(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const bytes = Array.from(new Uint8Array(digest));
  return bytes
    .slice(0, 8)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

function canvasProbe(): string {
  try {
    const c = document.createElement("canvas");
    c.width = 120;
    c.height = 40;
    const ctx = c.getContext("2d");
    if (!ctx) return "no-ctx";
    ctx.textBaseline = "top";
    ctx.font = "14px Arial";
    ctx.fillStyle = "#f60";
    ctx.fillRect(0, 0, 120, 40);
    ctx.fillStyle = "#069";
    ctx.fillText("aegis-local", 4, 4);
    return c.toDataURL().slice(-64);
  } catch {
    return "canvas-blocked";
  }
}

function webglInfo(): { vendor: string | null; renderer: string | null } {
  try {
    const c = document.createElement("canvas");
    const gl =
      (c.getContext("webgl") as WebGLRenderingContext | null) ||
      (c.getContext("experimental-webgl") as WebGLRenderingContext | null);
    if (!gl) return { vendor: null, renderer: null };
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    if (!ext) return { vendor: null, renderer: null };
    return {
      vendor: String(gl.getParameter(ext.UNMASKED_VENDOR_WEBGL)),
      renderer: String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)),
    };
  } catch {
    return { vendor: null, renderer: null };
  }
}

export async function collectFingerprint(): Promise<FingerprintSignals> {
  const nav = navigator as Navigator & { deviceMemory?: number; webdriver?: boolean };
  const webgl = webglInfo();
  const canvasRaw = canvasProbe();
  return {
    webdriver: Boolean(nav.webdriver),
    language: navigator.language,
    platform: navigator.platform,
    hardwareConcurrency: navigator.hardwareConcurrency || 0,
    deviceMemory: nav.deviceMemory ?? null,
    maxTouchPoints: navigator.maxTouchPoints || 0,
    timezoneOffset: new Date().getTimezoneOffset(),
    canvasHash: await sha256Short(canvasRaw),
    webglVendor: webgl.vendor,
    webglRenderer: webgl.renderer,
  };
}
