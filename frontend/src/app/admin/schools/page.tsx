"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Building2, CheckCircle2, Cloud, Plus, School, Users, XCircle } from "lucide-react";
import { authorizedFetch, getStoredUser, StoredUserInfo } from "@/lib/auth";
import { PanelLoading, ButtonSpinner } from "@/components/Spinner";

interface SchoolSummary {
  school_id: string;
  name: string;
  code: string;
  workspace_domain: string;
  is_active: boolean;
  teacher_count: number;
  department_count: number;
  drive_configured: boolean;
  created_at: string;
}

const emptyForm = {
  name: "",
  code: "",
  workspace_domain: "",
  google_drive_root_folder_id: "",
  grade_count: 3,
};

export default function AdminSchoolsPage() {
  const [schools, setSchools] = useState<SchoolSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [creating, setCreating] = useState(false);
  const [user, setUser] = useState<StoredUserInfo | null>(null);

  async function loadSchools() {
    setError(null);
    const res = await authorizedFetch("/admin/schools");
    if (!res.ok) {
      const detail = await res.json().catch(() => null);
      setError(detail?.detail || "학교 목록을 불러오지 못했습니다. 플랫폼 관리자(SUPER_ADMIN) 로그인이 필요합니다.");
      setSchools([]);
      return;
    }
    setSchools(await res.json());
  }

  useEffect(() => {
    setUser(getStoredUser());
    loadSchools();
  }, []);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    try {
      const res = await authorizedFetch("/admin/schools", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          grade_count: Number(form.grade_count) || 3,
          google_drive_root_folder_id: form.google_drive_root_folder_id || null,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "학교 등록에 실패했습니다.");
      setShowForm(false);
      setForm(emptyForm);
      await loadSchools();
    } catch (e) {
      setError(e instanceof Error ? e.message : "학교 등록 중 오류가 발생했습니다.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-800">
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2 text-sky-700 font-bold text-lg hover:opacity-80 transition">
            <School className="w-6 h-6" />
            <span>온라인 교무실</span>
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-semibold text-slate-600">전체 학교 현황 (플랫폼 관리자)</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" /> 신규 학교 등록
          </button>
          <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> 대시보드로
          </Link>
        </div>
      </header>

      <div className="flex-1 max-w-5xl mx-auto w-full p-6 space-y-6">
        {!user && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            플랫폼 관리자(SUPER_ADMIN) 계정으로 <Link href="/login" className="font-bold underline">로그인</Link> 후 이용하세요.
          </div>
        )}
        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{error}</div>}

        {showForm && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-3">
            <h2 className="text-sm font-bold text-slate-800">신규 학교 온보딩</h2>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <label className="space-y-1">
                <span className="text-slate-500">학교명</span>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full border border-slate-200 rounded px-2 py-1.5" placeholder="예: 대한고등학교" />
              </label>
              <label className="space-y-1">
                <span className="text-slate-500">학교 코드</span>
                <input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="w-full border border-slate-200 rounded px-2 py-1.5" placeholder="예: DAEHAN_HS" />
              </label>
              <label className="space-y-1">
                <span className="text-slate-500">Workspace 도메인</span>
                <input value={form.workspace_domain} onChange={(e) => setForm({ ...form, workspace_domain: e.target.value })} className="w-full border border-slate-200 rounded px-2 py-1.5" placeholder="예: daehan.hs.kr" />
              </label>
              <label className="space-y-1">
                <span className="text-slate-500">학년 수</span>
                <input type="number" min={1} max={6} value={form.grade_count} onChange={(e) => setForm({ ...form, grade_count: Number(e.target.value) })} className="w-full border border-slate-200 rounded px-2 py-1.5" />
              </label>
              <label className="space-y-1 col-span-2">
                <span className="text-slate-500">Google Drive 루트 폴더 ID (선택, 나중에 채워도 됨)</span>
                <input value={form.google_drive_root_folder_id} onChange={(e) => setForm({ ...form, google_drive_root_folder_id: e.target.value })} className="w-full border border-slate-200 rounded px-2 py-1.5" />
              </label>
            </div>
            <button
              onClick={handleCreate}
              disabled={creating || !form.name || !form.code || !form.workspace_domain}
              className="flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-70 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition"
            >
              {creating && <ButtonSpinner />}
              {creating ? "등록 중..." : "학교 등록"}
            </button>
          </div>
        )}

        {schools === null && <PanelLoading label="학교 목록을 불러오는 중입니다..." />}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {schools?.map((s) => (
            <div key={s.school_id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-800">{s.name}</h3>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${s.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>
                  {s.is_active ? "운영중" : "비활성"}
                </span>
              </div>
              <p className="text-xs text-slate-400">@{s.workspace_domain} · {s.code}</p>
              <div className="grid grid-cols-3 gap-2 text-xs pt-2 border-t border-slate-100">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Users className="w-3.5 h-3.5 text-sky-500" /> 교직원 {s.teacher_count}명
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Building2 className="w-3.5 h-3.5 text-indigo-500" /> 부서 {s.department_count}개
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Cloud className="w-3.5 h-3.5 text-slate-400" />
                  {s.drive_configured ? (
                    <span className="text-emerald-700 flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Drive 연동</span>
                  ) : (
                    <span className="text-slate-400 flex items-center gap-1"><XCircle className="w-3 h-3" /> Drive 미설정</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {schools?.length === 0 && !error && (
          <p className="text-center text-xs text-slate-400 py-10">등록된 학교가 없습니다. 우측 상단에서 신규 학교를 등록하세요.</p>
        )}
      </div>
    </div>
  );
}
