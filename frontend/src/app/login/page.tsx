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

  const [pwEmail, setPwEmail] = useState("");
  const [pwPassword, setPwPassword] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState<string | null>(null);

  async function finishLogin(res: Response) {
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error(data?.detail || "로그인에 실패했습니다.");
    }
    setSession(data.access_token, data.user_info);
    router.push("/");
  }

  async function handleCredentialResponse(response: { credential: string }) {
    setLoading(true);
    setError(null);
    try {
      await finishLogin(
        await fetch(`${API_BASE_URL}/auth/google/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id_token: response.credential }),
        })
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "로그인 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  }

  async function handlePasswordLogin() {
    setPwLoading(true);
    setPwError(null);
    try {
      await finishLogin(
        await fetch(`${API_BASE_URL}/auth/password/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: pwEmail, password: pwPassword }),
        })
      );
    } catch (e) {
      setPwError(e instanceof Error ? e.message : "로그인 중 오류가 발생했습니다.");
    } finally {
      setPwLoading(false);
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

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 w-full max-w-sm space-y-5">
        <div className="flex items-center justify-center gap-2 text-sky-700 font-bold text-xl">
          <School className="w-6 h-6" />
          <span>온라인 교무실</span>
        </div>

        <div className="text-center space-y-3">
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

        <div className="flex items-center gap-2 text-[10px] text-slate-300">
          <div className="flex-1 h-px bg-slate-200" /> 또는 <div className="flex-1 h-px bg-slate-200" />
        </div>

        <div className="space-y-2">
          <p className="text-xs text-slate-500 text-center">
            구글 워크스페이스를 쓰지 않는 학교는 이메일/비밀번호로 로그인하세요.
          </p>
          <input
            type="email"
            value={pwEmail}
            onChange={(e) => setPwEmail(e.target.value)}
            placeholder="학교 이메일"
            className="w-full text-xs border border-slate-200 rounded px-3 py-2"
          />
          <input
            type="password"
            value={pwPassword}
            onChange={(e) => setPwPassword(e.target.value)}
            placeholder="비밀번호"
            onKeyDown={(e) => e.key === "Enter" && handlePasswordLogin()}
            className="w-full text-xs border border-slate-200 rounded px-3 py-2"
          />
          <button
            onClick={handlePasswordLogin}
            disabled={pwLoading || !pwEmail || !pwPassword}
            className="w-full py-2 bg-slate-700 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition"
          >
            {pwLoading ? "로그인 중..." : "이메일로 로그인"}
          </button>
          {pwError && <p className="text-xs text-rose-600 text-center">{pwError}</p>}
          <p className="text-[10px] text-slate-400 text-center">
            비밀번호는 학교 관리자가 교직원 등록 시 발급합니다. 모르면 관리자에게 문의하세요.
          </p>
        </div>
      </div>
    </div>
  );
}
