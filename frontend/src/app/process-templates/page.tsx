"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, FileText, Pencil, Plus, School, Trash2, User } from "lucide-react";
import { authorizedFetch, getStoredUser, StoredUserInfo } from "@/lib/auth";
import { PanelLoading, ButtonSpinner } from "@/components/Spinner";
import { logEvent } from "@/lib/analytics";

interface ProcessTemplate {
  id: string;
  school_id: string;
  department_id?: string;
  department_name?: string;
  category: string;
  title: string;
  description: string;
  required_items?: string;
  form_doc_url?: string;
  contact_teacher_id?: string;
  contact_teacher_name?: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

const EMPTY_FORM = {
  category: "",
  title: "",
  department_id: "",
  description: "",
  required_items: "",
  form_doc_url: "",
  contact_teacher_id: "",
};

const ADMIN_ROLES = ["SCHOOL_ADMIN", "DEPARTMENT_HEAD"];

function formatDateTime(value: string) {
  try {
    return new Date(value).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export default function ProcessTemplatesPage() {
  const [items, setItems] = useState<ProcessTemplate[] | null>(null);
  const [departments, setDepartments] = useState<{ id: string; name: string }[]>([]);
  const [teachers, setTeachers] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [user, setUser] = useState<StoredUserInfo | null>(null);

  const isAdmin = !!user && ADMIN_ROLES.includes(user.role);

  async function loadAll() {
    setError(null);
    const [listRes, metaRes] = await Promise.all([
      authorizedFetch("/process-templates"),
      authorizedFetch("/schools/meta"),
    ]);
    if (!listRes.ok) {
      const detail = await listRes.json().catch(() => null);
      setError(detail?.detail || "프로세스 목록을 불러오지 못했습니다. 로그인이 필요합니다.");
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
    logEvent("VIEW_PROCESS_TEMPLATES");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEditForm(t: ProcessTemplate) {
    setEditingId(t.id);
    setForm({
      category: t.category,
      title: t.title,
      department_id: t.department_id || "",
      description: t.description,
      required_items: t.required_items || "",
      form_doc_url: t.form_doc_url || "",
      contact_teacher_id: t.contact_teacher_id || "",
    });
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(EMPTY_FORM);
  }

  async function handleSave() {
    setBusy(true);
    setError(null);
    try {
      const payload = {
        category: form.category,
        title: form.title,
        department_id: form.department_id || undefined,
        description: form.description,
        required_items: form.required_items || undefined,
        form_doc_url: form.form_doc_url || undefined,
        contact_teacher_id: form.contact_teacher_id || undefined,
      };
      const res = await authorizedFetch(
        editingId ? `/process-templates/${editingId}` : "/process-templates",
        {
          method: editingId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "저장에 실패했습니다.");
      if (!editingId) logEvent("CREATE_PROCESS_TEMPLATE");
      closeForm();
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "저장 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(id: string, title: string) {
    if (!window.confirm(`"${title}" 항목을 삭제하시겠습니까?`)) return;
    setBusy(true);
    setError(null);
    try {
      const res = await authorizedFetch(`/process-templates/${id}`, { method: "DELETE" });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || "삭제에 실패했습니다.");
      }
      await loadAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "삭제 중 오류가 발생했습니다.");
    } finally {
      setBusy(false);
    }
  }

  const grouped = useMemo(() => {
    if (!items) return [];
    const map = new Map<string, ProcessTemplate[]>();
    for (const item of items) {
      const list = map.get(item.category) || [];
      list.push(item);
      map.set(item.category, list);
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0], "ko"));
  }, [items]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-800">
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2 text-sky-700 font-bold text-lg hover:opacity-80 transition">
            <School className="w-6 h-6" />
            <span>온라인 교무실</span>
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-semibold text-slate-600">업무 프로세스 &amp; 품의 양식</span>
        </div>
        <div className="flex items-center gap-4">
          {isAdmin && (
            <button
              onClick={openCreateForm}
              className="inline-flex items-center gap-1 px-3 py-1.5 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-lg shadow-sm transition"
            >
              <Plus className="w-3.5 h-3.5" /> 새 프로세스 등록
            </button>
          )}
          <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> 대시보드로
          </Link>
        </div>
      </header>

      <div className="flex-1 max-w-4xl mx-auto w-full p-6 space-y-6">
        <p className="text-xs text-slate-500 bg-white border border-slate-200 rounded-lg p-3">
          행정실 등에서 요구하는 처리 절차와 품의 양식을 표준화해 공개합니다. 담당자에 따라 요구사항이
          달라지는 문제를 줄이기 위한 것으로, 변경 시점은 각 카드 하단의 &quot;최근 수정&quot;에서 확인할 수 있습니다.
        </p>

        {!user && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            <Link href="/login" className="font-bold underline">로그인</Link> 후 이용하세요.
          </div>
        )}
        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{error}</div>}

        {showForm && isAdmin && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
            <h3 className="text-xs font-bold text-slate-600">{editingId ? "프로세스 수정" : "새 프로세스 등록"}</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <input
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
                placeholder="분류 (예: 구매품의, 외부강사비, 출장신청)"
                className="border border-slate-200 rounded px-2 py-1.5"
              />
              <input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="제목 (예: 소모품 구매 품의)"
                className="border border-slate-200 rounded px-2 py-1.5"
              />
              <select
                value={form.department_id}
                onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                className="border border-slate-200 rounded px-2 py-1.5"
              >
                <option value="">담당 부서 (선택, 보통 행정실)</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
              <select
                value={form.contact_teacher_id}
                onChange={(e) => setForm({ ...form, contact_teacher_id: e.target.value })}
                className="border border-slate-200 rounded px-2 py-1.5"
              >
                <option value="">문의 담당자 (선택)</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="처리 절차 (단계별로 작성)"
                rows={4}
                className="col-span-2 border border-slate-200 rounded px-2 py-1.5 resize-none"
              />
              <textarea
                value={form.required_items}
                onChange={(e) => setForm({ ...form, required_items: e.target.value })}
                placeholder="필요 서류/준비물 (선택)"
                rows={2}
                className="col-span-2 border border-slate-200 rounded px-2 py-1.5 resize-none"
              />
              <input
                value={form.form_doc_url}
                onChange={(e) => setForm({ ...form, form_doc_url: e.target.value })}
                placeholder="품의 양식 링크 (Google Docs/Sheets URL, 선택)"
                className="col-span-2 border border-slate-200 rounded px-2 py-1.5"
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={handleSave}
                disabled={busy || !form.category || !form.title || !form.description}
                className="flex items-center px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-70 disabled:cursor-not-allowed text-white text-xs font-bold rounded-lg transition"
              >
                {busy && <ButtonSpinner />}
                {busy ? "처리 중..." : editingId ? "수정 저장" : "등록"}
              </button>
              <button
                onClick={closeForm}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-bold rounded-lg transition"
              >
                취소
              </button>
            </div>
          </div>
        )}

        {items === null && <PanelLoading label="업무 매뉴얼을 불러오는 중입니다..." />}

        <div className="space-y-8">
          {grouped.map(([category, list]) => (
            <div key={category} className="space-y-3">
              <h2 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                <FileText className="w-4 h-4 text-sky-600" /> {category}
              </h2>
              <div className="space-y-3">
                {list.map((t) => (
                  <div key={t.id} className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-2">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-slate-800 text-sm">{t.title}</h3>
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-sky-50 text-sky-700 border border-sky-200">
                            {t.category}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-0.5">
                          {t.department_name || "부서 미지정"}
                          {t.contact_teacher_name && (
                            <span className="inline-flex items-center gap-0.5 ml-2">
                              <User className="w-3 h-3" /> {t.contact_teacher_name}
                            </span>
                          )}
                        </p>
                      </div>
                      {isAdmin && (
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => openEditForm(t)}
                            className="p-1.5 rounded hover:bg-slate-100 text-slate-500"
                            title="수정"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(t.id, t.title)}
                            className="p-1.5 rounded hover:bg-rose-50 text-rose-500"
                            title="삭제"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>

                    <p className="text-xs text-slate-600 whitespace-pre-wrap leading-relaxed">{t.description}</p>

                    {t.required_items && (
                      <div className="text-[11px] text-slate-500 bg-slate-50 rounded p-2">
                        <span className="font-bold">필요 서류/준비물: </span>
                        <span className="whitespace-pre-wrap">{t.required_items}</span>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-1">
                      {t.form_doc_url ? (
                        <a
                          href={t.form_doc_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-emerald-700 flex items-center gap-1 hover:underline"
                        >
                          <ExternalLink className="w-3.5 h-3.5" /> 품의 양식 열기
                        </a>
                      ) : (
                        <span className="text-[11px] text-slate-300">연결된 양식 없음</span>
                      )}
                      <span className="text-[10px] text-slate-400">최근 수정: {formatDateTime(t.updated_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
          {grouped.length === 0 && !error && items !== null && (
            <p className="text-center text-xs text-slate-400 py-10">등록된 프로세스가 없습니다.</p>
          )}
        </div>
      </div>
    </div>
  );
}
