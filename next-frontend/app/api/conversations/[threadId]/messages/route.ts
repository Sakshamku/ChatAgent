export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function POST(
  request: Request,
  context: { params: Promise<{ threadId: string }> }
) {
  const { threadId } = await context.params;
  const body = await request.json();

  const upstream = await fetch(
    `${BACKEND_URL}/conversations/${threadId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    }
  );

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text().catch(() => "Upstream request failed");
    return new Response(detail, { status: upstream.status });
  }

  const stream = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          if (value) controller.enqueue(value);
        }
      } catch (error) {
        controller.error(error);
      } finally {
        controller.close();
      }
    },
  });

  const headers = new Headers(upstream.headers);
  headers.set("Content-Type", "text/event-stream; charset=utf-8");
  headers.set("Cache-Control", "no-cache, no-transform");
  headers.set("Connection", "keep-alive");
  headers.set("X-Accel-Buffering", "no");
  headers.delete("content-length");

  return new Response(stream, {
    status: upstream.status,
    headers,
  });
}
