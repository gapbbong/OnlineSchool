"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Lightbulb, School } from "lucide-react";
import { authorizedFetch, getStoredUser } from "@/lib/auth";

interface Summary {
  total_events: number;
  total_tasks: number;
  event_counts: { event_type: string; count: number }[];
  tasks_by_department: { department_name: string; count: number }[];
  tasks_by_status: { status: string; count: number }[];
  tasks_by_priority: { priority: string; count: number }[];
  top_repeated_task_titles: { title: string; count: number }[];
  tasks_by_weekday: { weekday: string; count: number }[];
}

const EVENT_LABELS: Record<string, string> = {
  VIEW_DASHBOARD: "대시보드 조회",
  VIEW_CALENDAR_MONTH: "캘린더 - 월간",
  VIEW_CALENDAR_WEEK: "캘린더 - 주간",
  VIEW_CALENDAR_DAY: "캘린더 - 일간",
  VIEW_CALENDAR_LIST: "캘린더 - 목록",
  VIEW_TIMETABLE_TEACHER: "시간표 - 교사별",
  VIEW_TIMETABLE_CLASS: "시간표 - 학급별",
  SEND_MESSAGE_ANNOUNCEMENT: "메시지 - 전체공지 발송",
  SEND_MESSAGE_DEPARTMENT: "메시지 - 부서공지 발송",
  SEND_MESSAGE_DIRECT: "메시지 - 개인쪽지 발송",
  QUICK_TASK_CREATE: "빠른 업무 추가",
  BULK_IMPORT: "엑셀 일괄 등록",
  WORK_HANDOVER_CREATE: "인수인계 항목 등록",
  WORK_HANDOVER_TRANSFER: "인수인계 실행",
};

function Bar({ label, count, max }: { label: string; count: number; max: number }) {
  const pct = max > 0 ? Math.max((count / max) * 100, 3) : 0;
  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-600">{label}</span>
        <span className="font-bold text-slate-800">{count}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full bg-sky-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const user = getStoredUser();

  useEffect(() => {
    authorizedFetch("/analytics/summary")
      .then(async (res) => {
        if (!res.ok) {
          const detail = await res.json().catch(() => null);
          throw new Error(detail?.detail || "통계를 불러오지 못했습니다.");
        }
        return res.json();
      })
      .then(setSummary)
      .catch((e) => setError(e instanceof Error ? e.message : "오류가 발생했습니다."));
  }, []);

  const maxEvent = Math.max(1, ...(summary?.event_counts.map((e) => e.count) || [1]));
  const maxDept = Math.max(1, ...(summary?.tasks_by_department.map((d) => d.count) || [1]));
  const maxWeekday = Math.max(1, ...(summary?.tasks_by_weekday.map((d) => d.count) || [1]));

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
            <BarChart3 className="w-4 h-4" /> 사용 현황 & 업무 인사이트
          </span>
        </div>
        <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> 대시보드로
        </Link>
      </header>

      <div className="flex-1 max-w-5xl mx-auto w-full p-6 space-y-6">
        {!user && (
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-700">
            <Link href="/login" className="font-bold underline">관리자 로그인</Link> 후 이용하세요.
          </div>
        )}
        {error && <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">{error}</div>}

        {summary && (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h2 className="text-sm font-bold text-slate-800 mb-3">기능별 사용 빈도</h2>
                <p className="text-[11px] text-slate-400 mb-3">거의 안 쓰이는 기능이 있다면 위치를 바꾸거나 없애는 걸 고려해보세요.</p>
                <div className="space-y-2">
                  {summary.event_counts.length === 0 && <p className="text-xs text-slate-400">아직 기록된 사용 로그가 없습니다.</p>}
                  {summary.event_counts.map((e) => (
                    <Bar key={e.event_type} label={EVENT_LABELS[e.event_type] || e.event_type} count={e.count} max={maxEvent} />
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h2 className="text-sm font-bold text-slate-800 mb-3">부서별 업무량</h2>
                <p className="text-[11px] text-slate-400 mb-3">업무가 특정 부서에 쏠려있다면 인력/역할 재배분을 검토해보세요.</p>
                <div className="space-y-2">
                  {summary.tasks_by_department.length === 0 && <p className="text-xs text-slate-400">등록된 업무가 없습니다.</p>}
                  {summary.tasks_by_department.map((d) => (
                    <Bar key={d.department_name} label={d.department_name} count={d.count} max={maxDept} />
                  ))}
                </div>
              </div>
            </div>

            <div className="bg-white rounded-xl border border-amber-200 shadow-sm p-5">
              <h2 className="text-sm font-bold text-slate-800 mb-1 flex items-center gap-1.5">
                <Lightbulb className="w-4 h-4 text-amber-500" /> 반복되는 업무 Top {summary.top_repeated_task_titles.length}
              </h2>
              <p className="text-[11px] text-slate-400 mb-3">같은 제목의 업무가 여러 번 등록됐다면, 반복 업무로 자동화할 후보입니다.</p>
              {summary.top_repeated_task_titles.length === 0 ? (
                <p className="text-xs text-slate-400">아직 반복되는 업무가 없습니다.</p>
              ) : (
                <div className="space-y-1.5">
                  {summary.top_repeated_task_titles.map((t) => (
                    <div key={t.title} className="flex items-center justify-between text-xs bg-amber-50/60 rounded px-3 py-1.5">
                      <span className="text-slate-700">{t.title}</span>
                      <span className="font-bold text-amber-700">{t.count}회</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
                <h2 className="text-sm font-bold text-slate-800 mb-3">마감일 요일 분포</h2>
                <p className="text-[11px] text-slate-400 mb-3">특정 요일에 마감이 몰려있다면 업무 배분을 조정해보세요.</p>
                <div className="space-y-2">
                  {summary.tasks_by_weekday.map((d) => (
                    <Bar key={d.weekday} label={`${d.weekday}요일`} count={d.count} max={maxWeekday} />
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
                <div>
                  <h2 className="text-sm font-bold text-slate-800 mb-2">업무 상태 분포</h2>
                  <div className="flex flex-wrap gap-1.5">
                    {summary.tasks_by_status.map((s) => (
                      <span key={s.status} className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
                        {s.status} {s.count}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-800 mb-2">업무 우선순위 분포</h2>
                  <div className="flex flex-wrap gap-1.5">
                    {summary.tasks_by_priority.map((p) => (
                      <span key={p.priority} className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-1 rounded-full">
                        {p.priority} {p.count}
                      </span>
                    ))}
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 pt-1 border-t border-slate-100">
                  전체 업무 {summary.total_tasks}건 · 전체 사용 로그 {summary.total_events}건
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
