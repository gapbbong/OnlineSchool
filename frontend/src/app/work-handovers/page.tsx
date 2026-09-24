"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowRightLeft, Cloud, Plus, School, User } from "lucide-react";
import { authorizedFetch, getStoredUser, StoredUserInfo } from "@/lib/auth";

interface Handover {
  id: string;
  work_title: string;
  department_name?: string;
  current_teacher_id?: string;
  current_teacher_name?: string;
  drive_folder_id?: string;
  drive_folder_url?: string;
  handover_note?: string;
}

export default function WorkHandoverPage() {
  const [items, setItems] = useState<Handover[] | null>(null);
  const [departments, setDepartments] = useState<{ id: string; name: string }[]>([]);
  const [teachers, setTeachers] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ work_title: "", department_id: "", current_teacher_id: "", handover_note: "" });
  const [transferTarget, setTransferTarget] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [user, setUser] = useState<StoredUserInfo | null>(null);

  async function loadAll() {
    setError(null);
    const [listRes, metaRes] = await Promise.all([
      authorizedFetch("/work-handovers"),
      authorizedFetch("/schools/meta"),
    ]);
    if (!listRes.ok) {
      const detail = await listRes.json().catch(() => null);
      setError(detail?.detail || "인수인계 목록을 불러오지 못했습니다. 로그인이 필요합니다.");
      setItems([]);
      return;
    }
    setItems(await listRes.json());
    const meta = await metaRes.json().catch(() => null);
    if (meta) setDepartments(meta.departments || []);
    if (getStoredUser()) {
      const tRes = await authorizedFetch("/teachers");
      if (tRes.ok) setTeachers((await tRes.json()).map((t: { id: string; name: string }) => ({ id: t.id, name: t.name })));
    }
  }

  useEffect(() => {
    setUser(getStoredUser());
    loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate() {
    setBusy(true);
    setError(null);
    try {
      const res = await authorizedFetch("/work-handovers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          work_title: form.work_title,
          department_id: form.department_id || undefined,
          current_teacher_id: form.current_teacher_id || undefined,
          handover_note: form.handover_note || undefined,
        }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "등록에 실패했습니다.");
      setShowForm(false);
      setForm({ work_title: "", department_id: "", current_teacher_id: "", handover_note: "" });
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "등록 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleTransfer(id: string) {
    const newTeacherId = transferTarget[id];
    if (!newTeacherId) return;
    const newTeacherName = teachers.find((t) => t.id === newTeacherId)?.name || "선택한 선생님";
    if (!window.confirm(`${newTeacherName}(으)로 인수인계하시겠습니까?\n이후에도 되돌릴 수는 있지만, 담당자가 바로 바뀝니다.`)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await authorizedFetch(`/work-handovers/${id}/handover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_teacher_id: newTeacherId }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "인수인계 처리에 실패했습니다.");
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "인수인계 처리 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
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
          <span className="text-sm font-semibold text-slate-600">업무 인수인계</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="inline-flex items-center gap-1 px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" /> 담당업무 등록
          </button>
          <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> 대시보드로
          </Link>
        </div>
      </header>

      <div className="flex-1 max-w-4xl mx-auto w-full p-6 space-y-6">
        <p className="text-xs text-slate-500 bg-white border border-slate-200 rounded-lg p-3">
          담당업무 단위로 Google Drive 폴더와 인수인계 메모를 관리합니다. 담당자가 바뀌어도 폴더와 이전 메모는
          그대로 유지되고, 새 인계 기록만 맨 위에 쌓입니다 — 연말 인사이동 때 그대로 이어받으면 됩니다.
        </p>

        {!user && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            <Link href="/login" className="font-bold underline">로그인</Link> 후 이용하세요.
          </div>
        )}
        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{error}</div>}

        {showForm && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <div className="grid grid-cols-2 gap-3 text-xs">
              <input value={form.work_title} onChange={(e) => setForm({ ...form, work_title: e.target.value })} placeholder="담당업무명 (예: 방과후학교 담당)" className="col-span-2 border border-slate-200 rounded px-2 py-1.5" />
              <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })} className="border border-slate-200 rounded px-2 py-1.5">
                <option value="">부서 (선택)</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
              <select value={form.current_teacher_id} onChange={(e) => setForm({ ...form, current_teacher_id: e.target.value })} className="border border-slate-200 rounded px-2 py-1.5">
                <option value="">현재 담당자 (선택)</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <textarea value={form.handover_note} onChange={(e) => setForm({ ...form, handover_note: e.target.value })} placeholder="초기 메모 (선택)" rows={2} className="col-span-2 border border-slate-200 rounded px-2 py-1.5 resize-none" />
            </div>
            <button onClick={handleCreate} disabled={busy || !form.work_title} className="px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition">
              {busy ? "처리 중..." : "등록"}
            </button>
          </div>
        )}

        <div className="space-y-3">
          {items?.map((h) => (
            <div key={h.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-2">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-slate-800 text-sm">{h.work_title}</h3>
                  <p className="text-[11px] text-slate-400">{h.department_name || "부서 미지정"}</p>
                </div>
                {h.drive_folder_url ? (
                  <a href={h.drive_folder_url} target="_blank" rel="noopener noreferrer" className="text-[11px] text-emerald-700 flex items-center gap-1 hover:underline">
                    <Cloud className="w-3.5 h-3.5" /> Drive 폴더 열기
                  </a>
                ) : h.drive_folder_id ? (
                  <span className="text-[11px] text-amber-600 flex items-center gap-1" title="Google Drive 실연동 준비 중입니다. 연동이 완료되면 자동으로 링크가 활성화됩니다.">
                    <Cloud className="w-3.5 h-3.5" /> 폴더 준비됨 (Google 연동 대기)
                  </span>
                ) : (
                  <span className="text-[11px] text-slate-400 flex items-center gap-1"><Cloud className="w-3.5 h-3.5" /> 폴더 생성 중/미설정</span>
                )}
              </div>
              <div className="text-xs text-slate-600 flex items-center gap-1">
                <User className="w-3.5 h-3.5 text-sky-500" /> 현재 담당: <strong>{h.current_teacher_name || "미지정"}</strong>
              </div>
              {h.handover_note && (
                <pre className="text-[10.5px] text-slate-500 bg-slate-50 rounded p-2 whitespace-pre-wrap leading-relaxed max-h-24 overflow-y-auto">{h.handover_note}</pre>
              )}
              <div className="flex items-center gap-2 pt-1">
                <select
                  value={transferTarget[h.id] || ""}
                  onChange={(e) => setTransferTarget({ ...transferTarget, [h.id]: e.target.value })}
                  className="text-[11px] border border-slate-200 rounded px-2 py-1 flex-1"
                >
                  <option value="">새 담당자 선택</option>
                  {teachers.filter((t) => t.id !== h.current_teacher_id).map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
                <button
                  onClick={() => handleTransfer(h.id)}
                  disabled={busy || !transferTarget[h.id]}
                  className="inline-flex items-center gap-1 px-3 py-1 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white text-[11px] font-bold rounded transition"
                >
                  <ArrowRightLeft className="w-3 h-3" /> 인수인계
                </button>
              </div>
            </div>
          ))}
          {items?.length === 0 && !error && (
            <p className="text-center text-xs text-slate-400 py-10">등록된 인수인계 항목이 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}
