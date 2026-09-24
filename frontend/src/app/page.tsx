"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Calendar, Clock, ExternalLink, MessageSquare, Plus,
  User, Bell, ChevronLeft, ChevronRight, LogOut, LogIn,
  School, FileText, Search, Settings, UserPlus,
  X, FileSpreadsheet, ArrowRightLeft, Building2, Zap, BarChart3
} from "lucide-react";
import Link from "next/link";
import { authorizedFetch, clearSession, getStoredUser, StoredUserInfo } from "@/lib/auth";
import { logEvent } from "@/lib/analytics";

interface TaskItem {
  id: string;
  title: string;
  description?: string;
  department_name?: string;
  assignee_name?: string;
  start_datetime: string;
  due_datetime?: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED";
}

interface ShortcutItem {
  id: string;
  title: string;
  url: string;
  icon: string;
  category: string;
}

interface TimetableItem {
  id: string;
  period: number;
  subject_name: string;
  teacher_name: string;
  grade_number: number;
  class_number: number;
  room_name?: string;
  practice_room_name?: string;
  lesson_type: string;
}

interface MessageItem {
  id: string;
  sender_name: string;
  title?: string;
  content: string;
  created_at: string;
}

interface DashboardData {
  school_name: string;
  today_tasks: TaskItem[];
  shortcuts: ShortcutItem[];
  today_timetables: TimetableItem[];
  recent_messages: MessageItem[];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [user, setUser] = useState<StoredUserInfo | null>(null);
  const [selectedView, setSelectedView] = useState<"TEACHER" | "CLASS">("TEACHER");
  const [selectedTeacher, setSelectedTeacher] = useState("홍길동");
  const [selectedClass, setSelectedClass] = useState("3학년 2반");

  // ④ 4사분면 - 메시지 작성 (기존 학교 메신저 대체용)
  const [showComposer, setShowComposer] = useState(false);
  const [composeType, setComposeType] = useState<"ANNOUNCEMENT" | "DEPARTMENT" | "DIRECT">("ANNOUNCEMENT");
  const [composeDeptId, setComposeDeptId] = useState("");
  const [composeRecipientId, setComposeRecipientId] = useState("");
  const [composeTitle, setComposeTitle] = useState("");
  const [composeContent, setComposeContent] = useState("");
  const [composeLinkedTaskId, setComposeLinkedTaskId] = useState("");
  const [composeLinkedTimetableId, setComposeLinkedTimetableId] = useState("");
  const [departments, setDepartments] = useState<{ id: string; name: string }[]>([]);
  const [teacherOptions, setTeacherOptions] = useState<{ id: string; name: string }[]>([]);
  const [composeStatus, setComposeStatus] = useState<{ sending: boolean; error: string | null; done: boolean }>({
    sending: false, error: null, done: false,
  });

  // 플로팅 빠른 실행 버튼 + 빠른 업무 추가 팝업
  const [fabOpen, setFabOpen] = useState(false);
  const [showQuickTask, setShowQuickTask] = useState(false);
  const [quickTaskTitle, setQuickTaskTitle] = useState("");
  const [quickTaskDue, setQuickTaskDue] = useState("");
  const [quickTaskStatus, setQuickTaskStatus] = useState<{ saving: boolean; error: string | null }>({
    saving: false, error: null,
  });

  // 1사분면 캘린더 상태 (9월 ~ 내년 2월 학기 캘린더)
  const semesterMonths = [
    { label: "9월", year: 2026, month: 9 },
    { label: "10월", year: 2026, month: 10 },
    { label: "11월", year: 2026, month: 11 },
    { label: "12월", year: 2026, month: 12 },
    { label: "1월", year: 2027, month: 1 },
    { label: "2월", year: 2027, month: 2 },
  ];
  const [selectedMonthIdx, setSelectedMonthIdx] = useState(0); // 기본 9월
  const [selectedDateDay, setSelectedDateDay] = useState<number>(19); // 기본 오늘 19일
  const [calendarViewMode, setCalendarViewMode] = useState<"MONTH" | "WEEK" | "DAY" | "LIST">("MONTH");

  // 분할창 크기 조절 (가로 비율 %, 세로 비율 %)
  const [splitX, setSplitX] = useState(50); // 좌우 비율 (50% : 50%)
  const [splitY, setSplitY] = useState(50); // 상하 비율 (50% : 50%)
  const containerRef = useRef<HTMLDivElement>(null);
  const isDraggingX = useRef(false);
  const isDraggingY = useRef(false);

  // 마우스 드래그 조절 핸들러
  const handleMouseDownX = (e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingX.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

  const handleMouseDownY = (e: React.MouseEvent) => {
    e.preventDefault();
    isDraggingY.current = true;
    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";
  };

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();

    if (isDraggingX.current) {
      const newX = ((e.clientX - rect.left) / rect.width) * 100;
      if (newX >= 25 && newX <= 75) {
        setSplitX(newX);
      }
    }
    if (isDraggingY.current) {
      const newY = ((e.clientY - rect.top) / rect.height) * 100;
      if (newY >= 25 && newY <= 75) {
        setSplitY(newY);
      }
    }
  }, []);

  const handleMouseUp = useCallback(() => {
    isDraggingX.current = false;
    isDraggingY.current = false;
    document.body.style.cursor = "default";
    document.body.style.userSelect = "auto";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  useEffect(() => {
    setUser(getStoredUser());
    logEvent("VIEW_DASHBOARD");
  }, []);

  useEffect(() => {
    if (!showComposer || !user) return;
    authorizedFetch("/schools/meta")
      .then((res) => res.json())
      .then((json) => setDepartments(json.departments || []))
      .catch(() => {});
    if (composeType === "DIRECT" && teacherOptions.length === 0) {
      authorizedFetch("/teachers")
        .then((res) => res.json())
        .then((json) => setTeacherOptions((json || []).map((t: { id: string; name: string }) => ({ id: t.id, name: t.name }))))
        .catch(() => {});
    }
  }, [showComposer, composeType, user, teacherOptions.length]);

  async function handleSendMessage() {
    if (!composeContent.trim()) {
      setComposeStatus({ sending: false, error: "메시지 내용을 입력해주세요.", done: false });
      return;
    }
    setComposeStatus({ sending: true, error: null, done: false });
    try {
      const res = await authorizedFetch("/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          msg_type: composeType,
          target_department_id: composeType === "DEPARTMENT" ? composeDeptId : undefined,
          recipient_ids: composeType === "DIRECT" ? [composeRecipientId] : undefined,
          title: composeTitle || undefined,
          content: composeContent,
          linked_task_id: composeLinkedTaskId || undefined,
          linked_timetable_id: composeLinkedTimetableId || undefined,
        }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(body?.detail || "메시지 전송에 실패했습니다.");

      setComposeStatus({ sending: false, error: null, done: true });
      logEvent(`SEND_MESSAGE_${composeType}`);
      setComposeTitle("");
      setComposeContent("");
      setComposeLinkedTaskId("");
      setComposeLinkedTimetableId("");
      // 대시보드 메시지 미리보기 갱신
      authorizedFetch("/dashboard").then((r) => r.json()).then(setData).catch(() => {});
      setTimeout(() => setComposeStatus((s) => ({ ...s, done: false })), 2500);
    } catch (e) {
      setComposeStatus({ sending: false, error: e instanceof Error ? e.message : "전송 중 오류가 발생했습니다.", done: false });
    }
  }

  async function handleCreateQuickTask() {
    if (!quickTaskTitle.trim()) {
      setQuickTaskStatus({ saving: false, error: "업무 제목을 입력해주세요." });
      return;
    }
    setQuickTaskStatus({ saving: true, error: null });
    try {
      const res = await authorizedFetch("/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: quickTaskTitle,
          start_datetime: new Date().toISOString(),
          due_datetime: quickTaskDue ? new Date(quickTaskDue).toISOString() : undefined,
        }),
      });
      const body = await res.json().catch(() => null);
      if (!res.ok) throw new Error(body?.detail || "업무 추가에 실패했습니다.");

      logEvent("QUICK_TASK_CREATE");
      setQuickTaskTitle("");
      setQuickTaskDue("");
      setShowQuickTask(false);
      setQuickTaskStatus({ saving: false, error: null });
      authorizedFetch("/dashboard").then((r) => r.json()).then(setData).catch(() => {});
    } catch (e) {
      setQuickTaskStatus({ saving: false, error: e instanceof Error ? e.message : "오류가 발생했습니다." });
    }
  }

  useEffect(() => {
    authorizedFetch("/dashboard")
      .then((res) => res.json())
      .then((json) => setData(json))
      .catch(() => {
        setData({
          school_name: "한국과학기술고등학교",
          today_tasks: [
            {
              id: "1",
              title: "교직원 회의 및 주간 업무 공유",
              description: "2학기 학사일정 점검 및 부서별 협의",
              department_name: "교무부",
              assignee_name: "홍길동",
              start_datetime: "2026-09-19T09:00:00",
              due_datetime: "2026-09-19T10:00:00",
              priority: "HIGH",
              status: "COMPLETED"
            },
            {
              id: "2",
              title: "3학년 2학기 평가계획서 제출 마감",
              description: "수행평가 및 지필평가 세부 기준 취합",
              department_name: "연구부",
              assignee_name: "김철수",
              start_datetime: "2026-09-19T10:00:00",
              due_datetime: "2026-09-19T17:00:00",
              priority: "URGENT",
              status: "IN_PROGRESS"
            }
          ],
          shortcuts: [
            { id: "1", title: "교무자료실", url: "https://drive.google.com/drive/u/0/folders/1sulAaa2WDVqxePp3SlM7dmX3ofiww8pt", icon: "folder", category: "Google Drive" },
            { id: "2", title: "학교 업무 Sheets", url: "https://docs.google.com", icon: "file-spreadsheet", category: "공통문서" },
            { id: "3", title: "NEIS (나이스)", url: "https://neis.go.kr", icon: "book-open", category: "행정" },
            { id: "4", title: "Gmail", url: "https://mail.google.com", icon: "mail", category: "Google Workspace" },
            { id: "5", title: "Google Calendar", url: "https://calendar.google.com", icon: "calendar", category: "Google Workspace" },
            { id: "6", title: "Google Drive", url: "https://drive.google.com", icon: "cloud", category: "Google Workspace" }
          ],
          today_timetables: [
            { id: "1", period: 1, subject_name: "국어", teacher_name: "홍길동", grade_number: 3, class_number: 2, room_name: "302호", lesson_type: "일반수업" },
            { id: "2", period: 2, subject_name: "영어", teacher_name: "이영희", grade_number: 3, class_number: 2, room_name: "303호", lesson_type: "일반수업" },
            { id: "3", period: 3, subject_name: "정보", teacher_name: "김철수", grade_number: 3, class_number: 2, room_name: "302호", practice_room_name: "컴퓨터실 B", lesson_type: "실습수업" },
            { id: "4", period: 4, subject_name: "공강", teacher_name: "-", grade_number: 0, class_number: 0, lesson_type: "-" }
          ],
          recent_messages: [
            { id: "1", sender_name: "김철수", title: "컴퓨터실 사용 안내", content: "오늘 3~4교시 컴퓨터실 B 실습 수업 진행 예정입니다.", created_at: "오전 08:45" },
            { id: "2", sender_name: "이영희", title: "3학년 회의실 변경", content: "오늘 15시 부서 회의는 제2협의실에서 진행됩니다.", created_at: "어제" }
          ]
        });
      });
  }, []);

  // 선택된 달의 캘린더 그리드 날짜 계산 (일~토)
  const currentMonth = semesterMonths[selectedMonthIdx];
  const daysInMonth = new Date(currentMonth.year, currentMonth.month, 0).getDate();
  const firstDayIndex = new Date(currentMonth.year, currentMonth.month - 1, 1).getDay(); // 0: 일요일, 6: 토요일
  const selectedDate = new Date(currentMonth.year, currentMonth.month - 1, selectedDateDay);

  const toDateKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

  // 업무를 날짜별로 묶어서 달력/주간/일간 뷰에서 공통으로 사용 (실제 데이터 기반)
  const tasksByDate: Record<string, TaskItem[]> = {};
  data?.today_tasks.forEach((task) => {
    const key = (task.start_datetime || task.due_datetime || "").slice(0, 10);
    if (!key) return;
    (tasksByDate[key] ||= []).push(task);
  });

  const selectedDayTasks = tasksByDate[toDateKey(selectedDate)] || [];

  // 선택된 날짜가 속한 주(일~토) 7일 계산
  const weekStart = new Date(selectedDate);
  weekStart.setDate(selectedDate.getDate() - selectedDate.getDay());
  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart);
    d.setDate(weekStart.getDate() + i);
    return d;
  });

  const formatTime = (iso?: string) => (iso ? iso.split("T")[1]?.slice(0, 5) : undefined);

  const selectDate = (d: Date) => {
    setSelectedDateDay(d.getDate());
    const idx = semesterMonths.findIndex((m) => m.year === d.getFullYear() && m.month === d.getMonth() + 1);
    if (idx >= 0) setSelectedMonthIdx(idx);
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-slate-100 text-slate-800 overflow-hidden">
      {/* 1. 상단 글로벌 네비게이션 헤더 (좌우 풀스크린 확장) */}
      <header className="bg-white border-b border-slate-200 px-4 py-2.5 flex items-center justify-between shadow-sm flex-shrink-0 z-50">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 text-sky-700 font-bold text-lg tracking-tight">
            <School className="w-5 h-5" />
            <span>온라인 교무실</span>
          </div>
          <span className="text-[11px] bg-sky-100 text-sky-800 px-2 py-0.5 rounded font-medium">
            {data?.school_name || "한국과학기술고등학교"}
          </span>
          <nav className="hidden lg:flex space-x-0.5 text-xs font-medium text-slate-600">
            {["홈", "업무", "캘린더", "시간표", "교직원", "학급", "부서", "자료실", "메시지", "통계"].map((menu, idx) => (
              <button
                key={menu}
                className={`px-2.5 py-1 rounded hover:bg-slate-100 transition ${
                  idx === 0 ? "bg-sky-50 text-sky-700 font-bold" : ""
                }`}
              >
                {menu}
              </button>
            ))}
            {/* 설정 드롭다운/메뉴로 신규 교사 등록 배치 */}
            <Link
              href="/teachers/onboarding"
              className="px-2.5 py-1 rounded hover:bg-slate-100 text-sky-700 font-semibold flex items-center gap-1 transition"
            >
              <UserPlus className="w-3.5 h-3.5 text-sky-600" />
              <span>설정 (새 교사 등록)</span>
            </Link>
          </nav>
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative hidden md:block">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2" />
            <input
              type="text"
              placeholder="교사, 업무, 학급, 시간표 통합 검색..."
              className="pl-8 pr-3 py-1 bg-slate-100 rounded-md text-xs focus:outline-none focus:ring-1 focus:ring-sky-500 w-56 transition"
            />
          </div>
          <button className="p-1.5 hover:bg-slate-100 rounded-full relative text-slate-600">
            <Bell className="w-4 h-4" />
            <span className="absolute top-1 right-1 w-1.5 h-1.5 bg-rose-500 rounded-full"></span>
          </button>
          {user ? (
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
              <div className="w-7 h-7 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-xs overflow-hidden">
                {user.photo_url ? (
                  <img src={user.photo_url} alt={user.name || user.email} className="w-full h-full object-cover" />
                ) : (
                  (user.name || user.email).slice(0, 1)
                )}
              </div>
              <div className="hidden sm:block text-left">
                <div className="text-xs font-semibold leading-none">{user.name || user.email} 선생님</div>
                <div className="text-[10px] text-slate-500 mt-0.5">{user.role}</div>
              </div>
              <button
                onClick={() => {
                  clearSession();
                  setUser(null);
                }}
                title="로그아웃"
                className="p-1 text-slate-400 hover:text-rose-600 transition"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="flex items-center gap-1 pl-2 border-l border-slate-200 text-xs font-semibold text-sky-700 hover:text-sky-800"
            >
              <LogIn className="w-3.5 h-3.5" /> 로그인
            </Link>
          )}
        </div>
      </header>

      {/* 2. 메인 4분할 조절 컨테이너 (좌우 여백 없이 가득 채움, 사분면 간 여백 1/4(p-1.5), 마우스 리사이징 가능) */}
      <main ref={containerRef} className="flex-1 w-full h-full p-1.5 relative overflow-hidden flex flex-col">
        
        {/* 상단 2개 영역 (1사분면, 2사분면) */}
        <div className="flex flex-1 overflow-hidden" style={{ height: `${splitY}%` }}>
          
          {/* ① 1사분면 - 업무 캘린더 (월간 요일/날짜 캘린더 및 9월~내년2월 탭) */}
          <div 
            className="bg-white rounded-lg shadow-sm border border-slate-200 p-3 flex flex-col overflow-hidden"
            style={{ width: `${splitX}%` }}
          >
            {/* 타이틀 바 & 9월~내년 2월 학기 탭 */}
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2 flex-shrink-0">
              <div className="flex items-center space-x-2">
                <Calendar className="w-4 h-4 text-sky-600" />
                <h3 className="font-bold text-slate-800 text-xs sm:text-sm">① 업무 캘린더</h3>
                <span className="text-[10px] px-1.5 py-0.2 bg-sky-50 text-sky-700 font-semibold rounded">
                  {currentMonth.year}년 {currentMonth.label}
                </span>
              </div>
              
              {/* 9월부터 내년 2월까지 탭 */}
              <div className="flex items-center bg-slate-100 p-0.5 rounded text-[11px] font-medium">
                {semesterMonths.map((m, idx) => (
                  <button
                    key={m.label}
                    onClick={() => setSelectedMonthIdx(idx)}
                    className={`px-1.5 py-0.5 rounded transition ${
                      selectedMonthIdx === idx 
                        ? "bg-white text-sky-700 font-bold shadow-xs" 
                        : "text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <div className="flex items-center space-x-1 text-[11px]">
                {([
                  ["MONTH", "월간"],
                  ["WEEK", "주간"],
                  ["DAY", "일간"],
                  ["LIST", "목록"],
                ] as const).map(([mode, label]) => (
                  <button
                    key={mode}
                    onClick={() => { setCalendarViewMode(mode); logEvent(`VIEW_CALENDAR_${mode}`); }}
                    className={`px-2 py-0.5 rounded font-medium ${calendarViewMode === mode ? "bg-sky-50 text-sky-700 font-bold" : "text-slate-500 hover:bg-slate-100"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* 캘린더 본문 */}
            {calendarViewMode === "MONTH" ? (
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* 요일 헤더 */}
                <div className="grid grid-cols-7 text-center text-[10px] font-bold text-slate-500 py-1 bg-slate-50 rounded mb-1">
                  <span className="text-rose-600">일</span>
                  <span>월</span>
                  <span>화</span>
                  <span>수</span>
                  <span>목</span>
                  <span>금</span>
                  <span className="text-sky-600">토</span>
                </div>
                
                {/* 날짜 그리드 */}
                <div className="grid grid-cols-7 gap-1 flex-1 overflow-y-auto auto-rows-fr text-center text-[11px]">
                  {/* 시작 요일 전 빈칸 */}
                  {Array.from({ length: firstDayIndex }).map((_, i) => (
                    <div key={`empty-${i}`} className="bg-slate-50/40 rounded border border-transparent"></div>
                  ))}
                  {/* 각 날짜 칸 */}
                  {Array.from({ length: daysInMonth }).map((_, i) => {
                    const day = i + 1;
                    const cellDate = new Date(currentMonth.year, currentMonth.month - 1, day);
                    const key = toDateKey(cellDate);
                    const todaysTasks = tasksByDate[key] || [];
                    const isToday = key === toDateKey(new Date());
                    const isSelected = selectedDateDay === day;

                    return (
                      <div
                        key={`day-${day}`}
                        onClick={() => setSelectedDateDay(day)}
                        className={`p-1 rounded border flex flex-col items-center justify-between cursor-pointer transition min-h-[32px] ${
                          isSelected
                            ? "border-sky-500 bg-sky-50/80 shadow-xs"
                            : isToday
                              ? "border-sky-300 bg-sky-50/40"
                              : "border-slate-100 hover:bg-slate-50"
                        }`}
                      >
                        <div className="w-full flex items-center justify-between px-0.5">
                          <span className={`text-[10px] font-semibold ${isToday ? "text-sky-700 font-black" : "text-slate-700"}`}>
                            {day}
                          </span>
                          {todaysTasks.length > 0 && (
                            <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                          )}
                        </div>
                        {todaysTasks.length > 0 && (
                          <span className="text-[8px] truncate max-w-full text-slate-600 bg-white/80 px-0.5 rounded leading-tight">
                            {todaysTasks.length > 1 ? `${todaysTasks[0].title} 외 ${todaysTasks.length - 1}건` : todaysTasks[0].title}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* 선택한 날짜의 상세 업무 미리보기 */}
                <div className="pt-2 mt-1 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-600">
                  <div className="flex items-center gap-2 truncate">
                    <span className="font-bold text-sky-700">{currentMonth.month}월 {selectedDateDay}일:</span>
                    <span className="truncate">
                      {selectedDayTasks.length > 0
                        ? selectedDayTasks.map((t) => `${t.title} (${formatTime(t.start_datetime) || "종일"})`).join(", ")
                        : "등록된 업무 일정이 없습니다."}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowQuickTask(true)}
                    className="text-sky-600 font-bold hover:underline flex-shrink-0 flex items-center gap-0.5"
                  >
                    + 일정 추가
                  </button>
                </div>
              </div>
            ) : calendarViewMode === "WEEK" ? (
              /* 주간 뷰 */
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="grid grid-cols-7 gap-1 flex-1 overflow-y-auto text-[11px]">
                  {weekDays.map((d, idx) => {
                    const key = toDateKey(d);
                    const dayTasks = tasksByDate[key] || [];
                    const isToday = key === toDateKey(new Date());
                    const isSelected = key === toDateKey(selectedDate);
                    return (
                      <div
                        key={key}
                        onClick={() => selectDate(d)}
                        className={`rounded border p-1.5 flex flex-col gap-1 cursor-pointer transition min-h-[120px] ${
                          isSelected ? "border-sky-500 bg-sky-50/80" : isToday ? "border-sky-300 bg-sky-50/40" : "border-slate-100 hover:bg-slate-50"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className={idx === 0 ? "text-rose-600 font-bold" : idx === 6 ? "text-sky-600 font-bold" : "text-slate-600 font-semibold"}>
                            {["일", "월", "화", "수", "목", "금", "토"][idx]}
                          </span>
                          <span className={`text-[10px] ${isToday ? "text-sky-700 font-black" : "text-slate-500"}`}>{d.getMonth() + 1}/{d.getDate()}</span>
                        </div>
                        <div className="space-y-0.5 overflow-y-auto">
                          {dayTasks.map((t) => (
                            <div key={t.id} className="text-[9px] bg-white border border-slate-100 rounded px-1 py-0.5 truncate" title={t.title}>
                              {t.title}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : calendarViewMode === "DAY" ? (
              /* 일간 뷰 */
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className="flex items-center justify-between pb-2 mb-1 border-b border-slate-100 flex-shrink-0">
                  <button onClick={() => selectDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate() - 1))} className="p-1 rounded hover:bg-slate-100">
                    <ChevronLeft className="w-3.5 h-3.5 text-slate-500" />
                  </button>
                  <span className="text-xs font-bold text-slate-700">
                    {selectedDate.getFullYear()}년 {selectedDate.getMonth() + 1}월 {selectedDate.getDate()}일 ({["일", "월", "화", "수", "목", "금", "토"][selectedDate.getDay()]})
                  </span>
                  <button onClick={() => selectDate(new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate() + 1))} className="p-1 rounded hover:bg-slate-100">
                    <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                  </button>
                </div>
                <div className="space-y-2 flex-1 overflow-y-auto">
                  {selectedDayTasks.length === 0 && (
                    <p className="text-center text-[11px] text-slate-400 py-8">이 날짜에 등록된 업무 일정이 없습니다.</p>
                  )}
                  {selectedDayTasks.map((task) => (
                    <div key={task.id} className="p-2.5 rounded border border-slate-100 bg-slate-50 flex items-start justify-between">
                      <div className="space-y-0.5">
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-bold text-sky-700">{formatTime(task.start_datetime) || "종일"}</span>
                          <h4 className="text-xs font-semibold text-slate-800">{task.title}</h4>
                        </div>
                        <p className="text-[11px] text-slate-500">{task.description}</p>
                        <span className="text-[10px] text-slate-400">담당: {task.assignee_name || "-"} · {task.department_name}</span>
                      </div>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${task.status === "COMPLETED" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                        {task.status === "COMPLETED" ? "완료" : "진행중"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              /* 목록 뷰 */
              <div className="space-y-2 flex-1 overflow-y-auto">
                {data?.today_tasks.map((task) => (
                  <div
                    key={task.id}
                    className="p-2.5 rounded border border-slate-100 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-200 transition flex items-start justify-between cursor-pointer"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center space-x-2">
                        <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded ${
                          task.priority === "URGENT" ? "bg-rose-100 text-rose-700" : "bg-sky-100 text-sky-700"
                        }`}>
                          {task.department_name}
                        </span>
                        <h4 className="text-xs font-semibold text-slate-800">{task.title}</h4>
                      </div>
                      <p className="text-[11px] text-slate-500">{task.description}</p>
                      <div className="flex items-center space-x-2 text-[10px] text-slate-400">
                        <span>담당: {task.assignee_name}</span>
                        <span>·</span>
                        <span>마감: {task.due_datetime?.split("T")[1]?.slice(0, 5) || "17:00"}</span>
                      </div>
                    </div>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                      task.status === "COMPLETED" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                    }`}>
                      {task.status === "COMPLETED" ? "완료" : "진행중"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 좌우 리사이즈 핸들 (상단) */}
          <div
            onMouseDown={handleMouseDownX}
            className="w-1.5 hover:w-2 bg-transparent hover:bg-sky-400 cursor-col-resize flex-shrink-0 transition-all z-20 flex items-center justify-center group"
          >
            <div className="w-0.5 h-6 bg-slate-300 group-hover:bg-white rounded"></div>
          </div>

          {/* ② 2사분면 - 자주 쓰는 바로가기 */}
          <div 
            className="bg-white rounded-lg shadow-sm border border-slate-200 p-3 flex flex-col overflow-hidden"
            style={{ width: `${100 - splitX}%` }}
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2 flex-shrink-0">
              <div className="flex items-center space-x-2">
                <ExternalLink className="w-4 h-4 text-indigo-600" />
                <h3 className="font-bold text-slate-800 text-xs sm:text-sm">② 자주 쓰는 바로가기</h3>
              </div>
              <button className="text-[11px] px-2 py-0.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium flex items-center gap-1">
                <Plus className="w-3 h-3" /> 추가
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 flex-1 overflow-y-auto content-start">
              {data?.shortcuts.map((sc) => (
                <a
                  key={sc.id}
                  href={sc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-2.5 rounded border border-slate-100 bg-slate-50 hover:bg-indigo-50/50 hover:border-indigo-200 transition flex flex-col justify-between group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold text-slate-500 group-hover:text-indigo-600">{sc.category}</span>
                    <ExternalLink className="w-3 h-3 text-slate-400 group-hover:text-indigo-500" />
                  </div>
                  <div className="mt-2">
                    <div className="text-xs font-bold text-slate-800 group-hover:text-indigo-700 truncate">{sc.title}</div>
                    <div className="text-[9px] text-slate-400 truncate mt-0.5">{sc.url}</div>
                  </div>
                </a>
              ))}
            </div>

            <div className="pt-2 mt-1 border-t border-slate-100 text-[10px] text-slate-400 flex items-center justify-between flex-shrink-0">
              <span>드라이브 루트: <code className="bg-slate-100 px-1 py-0.2 rounded text-[10px] text-slate-600">1sulAaa2...</code></span>
              <span className="text-indigo-600 font-semibold cursor-pointer hover:underline">드라이브 설정</span>
            </div>
          </div>

        </div>

        {/* 상하 리사이즈 핸들 (중앙 가로 바) */}
        <div
          onMouseDown={handleMouseDownY}
          className="h-1.5 hover:h-2 bg-transparent hover:bg-sky-400 cursor-row-resize flex-shrink-0 transition-all z-20 flex items-center justify-center group"
        >
          <div className="h-0.5 w-12 bg-slate-300 group-hover:bg-white rounded"></div>
        </div>

        {/* 하단 2개 영역 (3사분면, 4사분면) */}
        <div className="flex flex-1 overflow-hidden" style={{ height: `${100 - splitY}%` }}>
          
          {/* ③ 3사분면 - 시간표 / 수업실 */}
          <div 
            className="bg-white rounded-lg shadow-sm border border-slate-200 p-3 flex flex-col overflow-hidden"
            style={{ width: `${splitX}%` }}
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2 flex-shrink-0">
              <div className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-emerald-600" />
                <h3 className="font-bold text-slate-800 text-xs sm:text-sm">③ 시간표 / 수업실</h3>
              </div>
              <div className="flex items-center space-x-2">
                <div className="bg-slate-100 p-0.5 rounded flex text-[10px] font-semibold">
                  <button
                    onClick={() => { setSelectedView("TEACHER"); logEvent("VIEW_TIMETABLE_TEACHER"); }}
                    className={`px-2 py-0.5 rounded ${selectedView === "TEACHER" ? "bg-white text-emerald-700 shadow-xs" : "text-slate-600"}`}
                  >
                    교사별
                  </button>
                  <button
                    onClick={() => { setSelectedView("CLASS"); logEvent("VIEW_TIMETABLE_CLASS"); }}
                    className={`px-2 py-0.5 rounded ${selectedView === "CLASS" ? "bg-white text-emerald-700 shadow-xs" : "text-slate-600"}`}
                  >
                    학급별
                  </button>
                </div>
                {selectedView === "TEACHER" ? (
                  <select
                    value={selectedTeacher}
                    onChange={(e) => setSelectedTeacher(e.target.value)}
                    className="text-[11px] bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5 font-medium focus:outline-none"
                  >
                    <option value="홍길동">홍길동 선생님</option>
                    <option value="김철수">김철수 선생님</option>
                  </select>
                ) : (
                  <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="text-[11px] bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5 font-medium focus:outline-none"
                  >
                    <option value="3학년 2반">3학년 2반</option>
                    <option value="3학년 1반">3학년 1반</option>
                  </select>
                )}
              </div>
            </div>

            <div className="space-y-1.5 flex-1 overflow-y-auto">
              {data?.today_timetables.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center p-2 rounded border border-slate-100 bg-slate-50 hover:bg-emerald-50/50 hover:border-emerald-200 transition justify-between"
                >
                  <div className="flex items-center space-x-2.5">
                    <span className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px] flex items-center justify-center flex-shrink-0">
                      {item.period}
                    </span>
                    <div>
                      <div className="flex items-center space-x-1.5">
                        <span className="text-xs font-bold text-slate-800">{item.subject_name}</span>
                        {item.grade_number > 0 && (
                          <span className="text-[10px] text-slate-500 font-medium">({item.grade_number}-{item.class_number})</span>
                        )}
                        <span className="text-[10px] text-slate-400">· {item.teacher_name}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-[10px] text-slate-500">
                        {item.room_name && <span>교실: {item.room_name}</span>}
                        {item.practice_room_name && (
                          <span className="text-emerald-700 font-semibold bg-emerald-50 px-1 rounded border border-emerald-200 text-[9px]">
                            실습실: {item.practice_room_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] text-slate-400">{item.lesson_type}</span>
                </div>
              ))}
            </div>

            <div className="pt-2 mt-1 border-t border-slate-100 text-[10px] text-slate-500 flex justify-between flex-shrink-0">
              <span>화요일 기준 시간표</span>
              <button className="text-emerald-700 font-semibold hover:underline">전체 주간 시간표</button>
            </div>
          </div>

          {/* 좌우 리사이즈 핸들 (하단) */}
          <div
            onMouseDown={handleMouseDownX}
            className="w-1.5 hover:w-2 bg-transparent hover:bg-sky-400 cursor-col-resize flex-shrink-0 transition-all z-20 flex items-center justify-center group"
          >
            <div className="w-0.5 h-6 bg-slate-300 group-hover:bg-white rounded"></div>
          </div>

          {/* ④ 4사분면 - 교직원 메시지 */}
          <div 
            className="bg-white rounded-lg shadow-sm border border-slate-200 p-3 flex flex-col overflow-hidden"
            style={{ width: `${100 - splitX}%` }}
          >
            <div className="flex items-center justify-between pb-2 border-b border-slate-100 mb-2 flex-shrink-0">
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-4 h-4 text-amber-600" />
                <h3 className="font-bold text-slate-800 text-xs sm:text-sm">④ 교직원 메시지</h3>
              </div>
              <div className="flex items-center space-x-2">
                <div className="bg-slate-100 p-0.5 rounded flex text-[10px] font-semibold">
                  {([["ANNOUNCEMENT", "전체"], ["DEPARTMENT", "부서"], ["DIRECT", "개인"]] as const).map(([type, label]) => (
                    <button
                      key={type}
                      onClick={() => setComposeType(type)}
                      className={`px-1.5 py-0.5 rounded ${composeType === type ? "bg-white text-amber-700 shadow-xs" : "text-slate-600"}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => (user ? setShowComposer((v) => !v) : undefined)}
                  className="text-[10px] px-2 py-0.5 bg-amber-50 hover:bg-amber-100 text-amber-800 rounded font-semibold transition"
                >
                  {showComposer ? "닫기" : "작성"}
                </button>
              </div>
            </div>

            {showComposer && (
              <div className="mb-2 p-2.5 rounded-lg border border-amber-200 bg-amber-50/40 space-y-2 flex-shrink-0">
                {!user ? (
                  <p className="text-[11px] text-amber-700">
                    메시지를 보내려면 <Link href="/login" className="font-bold underline">로그인</Link>이 필요합니다.
                  </p>
                ) : (
                  <>
                    {composeType === "DEPARTMENT" && (
                      <select value={composeDeptId} onChange={(e) => setComposeDeptId(e.target.value)} className="w-full text-[11px] border border-slate-200 rounded px-2 py-1">
                        <option value="">부서 선택</option>
                        {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                      </select>
                    )}
                    {composeType === "DIRECT" && (
                      <select value={composeRecipientId} onChange={(e) => setComposeRecipientId(e.target.value)} className="w-full text-[11px] border border-slate-200 rounded px-2 py-1">
                        <option value="">받는 선생님 선택</option>
                        {teacherOptions.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                    )}
                    <input
                      value={composeTitle}
                      onChange={(e) => setComposeTitle(e.target.value)}
                      placeholder="제목 (선택)"
                      className="w-full text-[11px] border border-slate-200 rounded px-2 py-1"
                    />
                    <textarea
                      value={composeContent}
                      onChange={(e) => setComposeContent(e.target.value)}
                      placeholder="내용을 입력하세요"
                      rows={2}
                      className="w-full text-[11px] border border-slate-200 rounded px-2 py-1 resize-none"
                    />
                    <div className="grid grid-cols-2 gap-1.5">
                      <select value={composeLinkedTaskId} onChange={(e) => setComposeLinkedTaskId(e.target.value)} className="text-[10px] border border-slate-200 rounded px-1.5 py-1 text-slate-600">
                        <option value="">+ 업무 연결 (선택)</option>
                        {data?.today_tasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
                      </select>
                      <select value={composeLinkedTimetableId} onChange={(e) => setComposeLinkedTimetableId(e.target.value)} className="text-[10px] border border-slate-200 rounded px-1.5 py-1 text-slate-600">
                        <option value="">+ 시간표/실습실 연결 (선택)</option>
                        {data?.today_timetables.map((t) => (
                          <option key={t.id} value={t.id}>{t.period}교시 {t.subject_name}{t.practice_room_name ? ` (${t.practice_room_name})` : t.room_name ? ` (${t.room_name})` : ""}</option>
                        ))}
                      </select>
                    </div>

                    <p className="text-[9.5px] text-slate-500 leading-snug flex items-start gap-1">
                      🔒 개인 쪽지는 보낸 사람과 받는 사람만 볼 수 있고, 학교 관리자도 내용을 열람할 수 없습니다. (전체/부서 공지는 해당 대상 전원에게 공개됩니다)
                    </p>

                    <div className="flex items-center justify-between">
                      <span className="text-[10px]">
                        {composeStatus.error && <span className="text-rose-600">{composeStatus.error}</span>}
                        {composeStatus.done && <span className="text-emerald-600">전송 완료!</span>}
                      </span>
                      <button
                        onClick={handleSendMessage}
                        disabled={composeStatus.sending}
                        className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white text-[11px] font-bold rounded transition"
                      >
                        {composeStatus.sending ? "전송 중..." : "보내기"}
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            <div className="space-y-2 flex-1 overflow-y-auto">
              {data?.recent_messages.map((msg) => (
                <div
                  key={msg.id}
                  className="p-2 rounded border border-slate-100 bg-slate-50 hover:bg-amber-50/50 hover:border-amber-200 transition"
                >
                  <div className="flex items-center justify-between mb-0.5">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-xs font-bold text-slate-800">{msg.sender_name} 선생님</span>
                      {msg.title && (
                        <span className="text-[10px] text-amber-800 font-semibold bg-amber-100/70 px-1 py-0.2 rounded">
                          {msg.title}
                        </span>
                      )}
                    </div>
                    <span className="text-[9px] text-slate-400">{msg.created_at}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-snug">{msg.content}</p>
                </div>
              ))}
            </div>

            <div className="pt-2 mt-1 border-t border-slate-100 text-[10px] text-slate-500 flex justify-between flex-shrink-0">
              <span>안읽은 공지 1건</span>
              <button className="text-amber-700 font-semibold hover:underline">교직원 연락망</button>
            </div>
          </div>

        </div>
      </main>

      {/* 빠른 업무 추가 팝업 */}
      {showQuickTask && (
        <div className="fixed inset-0 bg-black/30 z-[100] flex items-center justify-center p-4" onClick={() => setShowQuickTask(false)}>
          <div className="bg-white rounded-xl shadow-lg w-full max-w-sm p-5 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-slate-800 text-sm flex items-center gap-1.5"><Plus className="w-4 h-4 text-sky-600" /> 빠른 업무 추가</h3>
              <button onClick={() => setShowQuickTask(false)} className="text-slate-400 hover:text-slate-700"><X className="w-4 h-4" /></button>
            </div>
            {!user ? (
              <p className="text-xs text-amber-700">
                업무를 추가하려면 <Link href="/login" className="font-bold underline">로그인</Link>이 필요합니다.
              </p>
            ) : (
              <>
                <input
                  autoFocus
                  value={quickTaskTitle}
                  onChange={(e) => setQuickTaskTitle(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateQuickTask()}
                  placeholder="업무 제목"
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2"
                />
                <input
                  type="datetime-local"
                  value={quickTaskDue}
                  onChange={(e) => setQuickTaskDue(e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2"
                />
                {quickTaskStatus.error && <p className="text-xs text-rose-600">{quickTaskStatus.error}</p>}
                <button
                  onClick={handleCreateQuickTask}
                  disabled={quickTaskStatus.saving}
                  className="w-full py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 text-white text-xs font-bold rounded-lg transition"
                >
                  {quickTaskStatus.saving ? "추가 중..." : "업무 추가"}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* 플로팅 빠른 실행 버튼 - 자주 쓰는 관리 화면으로 클릭 한 번에 이동 */}
      <div className="fixed bottom-6 right-6 z-[90] flex flex-col items-end gap-2">
        {fabOpen && (
          <div className="flex flex-col items-end gap-2 mb-1">
            {[
              { href: null, label: "빠른 업무 추가", icon: Plus, onClick: () => { setShowQuickTask(true); setFabOpen(false); } },
              { href: "/teachers/onboarding", label: "신규 교사 등록", icon: UserPlus },
              { href: "/teachers/bulk-import", label: "엑셀 일괄 등록", icon: FileSpreadsheet },
              { href: "/work-handovers", label: "업무 인수인계", icon: ArrowRightLeft },
              ...(user?.role === "SCHOOL_ADMIN" || user?.role === "DEPARTMENT_HEAD" || user?.role === "SUPER_ADMIN"
                ? [{ href: "/admin/analytics", label: "사용 현황 & 인사이트", icon: BarChart3 }]
                : []),
              ...(user?.role === "SUPER_ADMIN" ? [{ href: "/admin/schools", label: "학교 관리", icon: Building2 }] : []),
            ].map((item) => {
              const Icon = item.icon;
              const content = (
                <span className="flex items-center gap-2 bg-white shadow-md border border-slate-200 rounded-full pl-3 pr-1 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition">
                  {item.label}
                  <span className="w-7 h-7 rounded-full bg-sky-50 text-sky-600 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-3.5 h-3.5" />
                  </span>
                </span>
              );
              return item.href ? (
                <Link key={item.label} href={item.href} onClick={() => setFabOpen(false)}>{content}</Link>
              ) : (
                <button key={item.label} onClick={item.onClick}>{content}</button>
              );
            })}
          </div>
        )}
        <button
          onClick={() => setFabOpen((v) => !v)}
          className={`w-12 h-12 rounded-full shadow-lg flex items-center justify-center text-white transition ${fabOpen ? "bg-slate-700 rotate-45" : "bg-sky-600 hover:bg-sky-700"}`}
          title="빠른 실행"
        >
          {fabOpen ? <X className="w-5 h-5" /> : <Zap className="w-5 h-5" />}
        </button>
      </div>
    </div>
  );
}
