"use client";

import { API_BASE_URL } from "@/lib/api";

const TOKEN_KEY = "ofh_access_token";
const USER_KEY = "ofh_user_info";

export interface StoredUserInfo {
  user_id: string;
  school_id: string;
  school_name: string;
  email: string;
  role: string;
  name?: string;
  photo_url?: string;
}

// localStorage는 프라이빗 브라우징 등에서 접근이 막힐 수 있어 항상 try/catch로 감싼다.
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): StoredUserInfo | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as StoredUserInfo) : null;
  } catch {
    return null;
  }
}

export function setSession(token: string, user: StoredUserInfo) {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
    window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch {
    // 세션 유지만 안 될 뿐 로그인 자체는 이미 완료된 상태이므로 앱은 계속 동작한다.
  }
}

export function clearSession() {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(USER_KEY);
  } catch {
    // noop
  }
}

// 토큰이 있으면 Authorization 헤더를 붙이고, 없으면 그냥 익명 요청으로 보낸다.
// (대시보드 등 일부 조회 API는 비로그인 상태에서도 데모/부트스트랩용으로 열려 있음)
export async function authorizedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers });
}
