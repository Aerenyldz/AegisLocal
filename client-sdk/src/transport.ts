export interface TransportOptions {
  baseUrl: string;
  sessionId: string;
}

export class AegisTransport {
  constructor(private readonly opts: TransportOptions) {}

  async postJson<T>(path: string, body: unknown): Promise<T> {
    const res = await fetch(`${this.opts.baseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Aegis-Session": this.opts.sessionId,
      },
      body: JSON.stringify(body),
      credentials: "omit",
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`AegisLocal API ${res.status}: ${text}`);
    }
    return (await res.json()) as T;
  }
}
