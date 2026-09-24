"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { School } from "lucide-react";
import { API_BASE_URL } from "@/lib/api";
import { setSession } from "@/lib/auth";

declare global {
  interface Window {
    google?: any;
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleCredentialResponse(response: { credential: string }) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/google/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id_token: response.credential }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || "로그인에 실패했습니다.");
      }
      setSession(data.access_token, data.user_info);
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "로그인 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  function initGoogleButton() {
    if (!GOOGLE_CLIENT_ID || !window.google) return;
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: handleCredentialResponse,
    });
    const target = document.getElementById("google-signin-button");
    if (target) {
      window.google.accounts.id.renderButton(target, {
        theme: "outline",
        size: "large",
        text: "signin_with",
        width: 300,
      });
    }
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-slate-100">
      {GOOGLE_CLIENT_ID && (
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
          onLoad={initGoogleButton}
        />
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 w-full max-w-sm text-center space-y-4">
        <div className="flex items-center justify-center gap-2 text-sky-700 font-bold text-xl">
          <School className="w-6 h-6" />
          <span>온라인 교무실</span>
        </div>
        <p className="text-sm text-slate-500">학교 Google Workspace 계정으로 로그인하세요.</p>

        {GOOGLE_CLIENT_ID ? (
          <div id="google-signin-button" className="flex justify-center" />
        ) : (
          <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-3 text-left">
            Google 로그인이 아직 구성되지 않았습니다. 관리자가 <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code> 환경변수를
            설정해야 로그인 버튼이 표시됩니다.
          </p>
        )}

        {loading && <p className="text-xs text-slate-400">로그인 처리 중...</p>}
        {error && <p className="text-xs text-rose-600">{error}</p>}
      </div>
    </div>
  );
}
