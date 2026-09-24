"use client";

import { authorizedFetch } from "@/lib/auth";

// fire-and-forget 사용 로그 - 실패해도 화면 동작에 절대 영향을 주지 않는다.
export function logEvent(eventType: string, metadata?: Record<string, unknown>) {
  try {
    authorizedFetch("/analytics/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, metadata }),
    }).catch(() => {});
  } catch {
    // noop
  }
}
