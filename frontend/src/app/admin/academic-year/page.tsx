"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarPlus, Plus, School, Trash2 } from "lucide-react";
import { authorizedFetch, getStoredUser } from "@/lib/auth";

interface GradeCount {
  grade_number: number;
  class_count: number;
}

export default function AcademicYearPage() {
  const [currentYear, setCurrentYear] = useState<number | null>(null);
  const [newYear, setNewYear] = useState<number>(0);
  const [rows, setRows] = useState<GradeCount[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const user = getStoredUser();

  useEffect(() => {
    authorizedFetch("/admin/academic-year/structure")
      .then(async (res) => {
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail || "현재 학년도 구조를 불러오지 못했습니다.");
        }
        return res.json();
      })
      .then((data) => {
        setCurrentYear(data.academic_year);
        setNewYear(data.academic_year + 1);
        setRows(data.grades);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "오류가 발생했습니다."));
  }, []);

  function updateRow(idx: number, field: keyof GradeCount, value: number) {
    setRows((prev) => prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r)));
  }

  function addRow() {
    const nextGrade = (rows[rows.length - 1]?.grade_number || 0) + 1;
    setRows((prev) => [...prev, { grade_number: nextGrade, class_count: 1 }]);
  }

  function removeRow(idx: number) {
    setRows((prev) => prev.filter((_, i) => i !== idx));
  }

  async function handleTransition() {
    if (!currentYear) return;
    const totalClasses = rows.reduce((sum, r) => sum + r.class_count, 0);
    if (
      !window.confirm(
        `${newYear}학년도를 시작하시겠습니까?\n\n학년 ${rows.length}개, 반 ${totalClasses}개가 새로 생성됩니다.\n` +
          `${currentYear}학년도 데이터는 삭제되지 않고 이력으로 남지만, 담임/시간표는 새로 배정해야 합니다.`
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await authorizedFetch("/admin/academic-year/transition", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_academic_year: newYear, grade_class_counts: rows }),
      });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || "학년도 전환에 실패했습니다.");
      setResult(data.message);
      setCurrentYear(data.new_academic_year);
    } catch (e) {
      setError(e instanceof Error ? e.message : "오류가 발생했습니다.");
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
          <span className="text-sm font-semibold text-slate-600 flex items-center gap-1">
            <CalendarPlus className="w-4 h-4" /> 새 학년도 시작
          </span>
        </div>
        <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> 대시보드로
        </Link>
      </header>

      <div className="flex-1 max-w-2xl mx-auto w-full p-6 space-y-6">
        {!user && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            학교 관리자 <Link href="/login" className="font-bold underline">로그인</Link> 후 이용하세요.
          </div>
        )}
        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{error}</div>}
        {result && <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-700">{result}</div>}

        {currentYear !== null && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
            <p className="text-xs text-slate-500">
              현재 학년도: <strong className="text-slate-800">{currentYear}</strong> · 이전 학년도 반/시간표 데이터는
              전환 후에도 삭제되지 않고 그대로 조회할 수 있습니다. 담임과 시간표는 전환 후 별도 화면에서
              새로 배정해주세요.
            </p>

            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1">새 학년도</label>
              <input
                type="number"
                value={newYear}
                onChange={(e) => setNewYear(Number(e.target.value))}
                className="w-32 px-3 py-2 border border-slate-200 rounded-lg text-sm"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold text-slate-700">학년별 반 개수</label>
                <button onClick={addRow} className="text-[11px] text-sky-600 font-semibold flex items-center gap-0.5 hover:underline">
                  <Plus className="w-3 h-3" /> 학년 추가
                </button>
              </div>
              <div className="space-y-2">
                {rows.map((row, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="number"
                      value={row.grade_number}
                      onChange={(e) => updateRow(idx, "grade_number", Number(e.target.value))}
                      className="w-20 px-2 py-1.5 border border-slate-200 rounded text-xs"
                    />
                    <span className="text-xs text-slate-500">학년 ·</span>
                    <input
                      type="number"
                      value={row.class_count}
                      onChange={(e) => updateRow(idx, "class_count", Number(e.target.value))}
                      className="w-20 px-2 py-1.5 border border-slate-200 rounded text-xs"
                    />
                    <span className="text-xs text-slate-500">반</span>
                    <button onClick={() => removeRow(idx)} className="ml-auto text-slate-300 hover:text-rose-500">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={handleTransition}
              disabled={busy || rows.length === 0}
              className="w-full py-2.5 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-sm font-bold rounded-lg transition"
            >
              {busy ? "처리 중..." : `${newYear}학년도 시작`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
