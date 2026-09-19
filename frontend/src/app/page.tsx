"use client";

import React, { useEffect, useState } from "react";
import { 
  Calendar, Clock, ExternalLink, MessageSquare, Plus, 
  Settings, User, Bell, ChevronLeft, ChevronRight,
  School, CheckCircle2, AlertCircle, FileText, Search,
  GraduationCap, Building2, BookOpen
} from "lucide-react";

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
  const [loading, setLoading] = useState(true);
  const [selectedView, setSelectedView] = useState<"TEACHER" | "CLASS">("TEACHER");
  const [selectedTeacher, setSelectedTeacher] = useState("홍길동");
  const [selectedClass, setSelectedClass] = useState("3학년 2반");

  useEffect(() => {
    // API 호출 또는 폴백 기본 데이터
    fetch("http://localhost:8000/api/v1/dashboard")
      .then((res) => res.json())
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch(() => {
        // 백엔드 미구동 시에도 UI 검증이 가능한 정적 목 데이터
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
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-slate-100 text-slate-800">
      {/* 1. 상단 글로벌 네비게이션 헤더 */}
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shadow-sm sticky top-0 z-50">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2 text-sky-700 font-bold text-xl tracking-tight">
            <School className="w-6 h-6" />
            <span>온라인 교무실</span>
          </div>
          <span className="text-xs bg-sky-100 text-sky-800 px-2 py-1 rounded font-medium">
            {data?.school_name || "학교 로딩중..."}
          </span>
          <nav className="hidden lg:flex space-x-1 text-sm font-medium text-slate-600">
            {["홈", "업무", "캘린더", "시간표", "교직원", "학급", "부서", "자료실", "메시지", "통계", "설정"].map((menu, idx) => (
              <button
                key={menu}
                className={`px-3 py-1.5 rounded-md hover:bg-slate-100 transition ${
                  idx === 0 ? "bg-sky-50 text-sky-700 font-semibold" : ""
                }`}
              >
                {menu}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center space-x-4">
          <div className="relative hidden md:block">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="교사, 업무, 학급, 시간표 통합 검색..."
              className="pl-9 pr-4 py-1.5 bg-slate-100 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 w-64 transition"
            />
          </div>
          <button className="p-2 hover:bg-slate-100 rounded-full relative text-slate-600">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full"></span>
          </button>
          <div className="flex items-center space-x-2 pl-2 border-l border-slate-200">
            <div className="w-8 h-8 rounded-full bg-sky-600 text-white flex items-center justify-center font-bold text-sm">
              홍
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs font-semibold leading-tight">홍길동 선생님</div>
              <div className="text-[11px] text-slate-500">교무부 · 관리자</div>
            </div>
          </div>
        </div>
      </header>

      {/* 2. 메인 컨텐츠 (상단 요약 바 + 4분할 그리드) */}
      <main className="flex-1 p-6 max-w-[1600px] mx-auto w-full flex flex-col space-y-5">
        
        {/* 오늘 한눈에 보기 요약 배너 */}
        <div className="bg-gradient-to-r from-sky-700 to-indigo-800 text-white p-4 rounded-xl shadow flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-white/10 rounded-lg">
              <Calendar className="w-6 h-6 text-sky-200" />
            </div>
            <div>
              <h2 className="text-base font-semibold">오늘의 일정 및 수업 요약</h2>
              <p className="text-xs text-sky-100">
                2026년 9월 19일 · 오늘 수업 2개 · 제출 마감 업무 1건이 남아있습니다.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button className="px-3 py-1.5 bg-white text-sky-800 rounded-lg text-xs font-semibold hover:bg-sky-50 transition shadow-sm">
              새 교사 등록 (/onboarding)
            </button>
            <button className="px-3 py-1.5 bg-sky-600/60 hover:bg-sky-600 border border-sky-400/40 rounded-lg text-xs font-semibold transition">
              + 새 업무 작성
            </button>
          </div>
        </div>

        {/* 4분할 반응형 대시보드 그리드 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
          
          {/* ① 1사분면 - 업무 캘린더 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-sky-600" />
                <h3 className="font-bold text-slate-800 text-base">① 업무 캘린더</h3>
                <span className="text-xs px-2 py-0.5 bg-slate-100 rounded text-slate-500 font-medium">9월 19일 (오늘)</span>
              </div>
              <div className="flex items-center space-x-1 text-xs">
                <button className="px-2.5 py-1 bg-sky-50 text-sky-700 font-semibold rounded">월</button>
                <button className="px-2.5 py-1 hover:bg-slate-100 rounded text-slate-600">주</button>
                <button className="px-2.5 py-1 hover:bg-slate-100 rounded text-slate-600">일</button>
              </div>
            </div>

            <div className="space-y-3 flex-1 overflow-y-auto">
              {data?.today_tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-3.5 rounded-lg border border-slate-100 bg-slate-50 hover:bg-sky-50/50 hover:border-sky-200 transition flex items-start justify-between group cursor-pointer"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        task.priority === "URGENT" ? "bg-rose-100 text-rose-700" : "bg-sky-100 text-sky-700"
                      }`}>
                        {task.department_name}
                      </span>
                      <h4 className="text-sm font-semibold text-slate-800 group-hover:text-sky-700">{task.title}</h4>
                    </div>
                    <p className="text-xs text-slate-500">{task.description}</p>
                    <div className="flex items-center space-x-3 text-[11px] text-slate-400 pt-1">
                      <span>담당: {task.assignee_name}</span>
                      <span>·</span>
                      <span>마감: {task.due_datetime?.split("T")[1]?.slice(0, 5) || "17:00"}</span>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded font-medium ${
                    task.status === "COMPLETED" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                  }`}>
                    {task.status === "COMPLETED" ? "완료" : "진행중"}
                  </span>
                </div>
              ))}
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Google Sheets 업무기록 자동 연동됨</span>
              <button className="text-sky-600 font-semibold hover:underline flex items-center gap-1">
                전체 업무 보기 <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* ② 2사분면 - 자주 쓰는 바로가기 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2">
                <ExternalLink className="w-5 h-5 text-indigo-600" />
                <h3 className="font-bold text-slate-800 text-base">② 자주 쓰는 바로가기</h3>
              </div>
              <button className="text-xs px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium flex items-center gap-1">
                <Plus className="w-3.5 h-3.5" /> 바로가기 추가
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 flex-1">
              {data?.shortcuts.map((sc) => (
                <a
                  key={sc.id}
                  href={sc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-3.5 rounded-lg border border-slate-100 bg-slate-50 hover:bg-indigo-50/50 hover:border-indigo-200 transition flex flex-col justify-between group"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 group-hover:text-indigo-600">{sc.category}</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400 group-hover:text-indigo-500" />
                  </div>
                  <div className="mt-3">
                    <div className="text-sm font-bold text-slate-800 group-hover:text-indigo-700">{sc.title}</div>
                    <div className="text-[11px] text-slate-400 truncate mt-0.5">{sc.url}</div>
                  </div>
                </a>
              ))}
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 text-xs text-slate-400 flex items-center justify-between">
              <span>학교 드라이브 루트: <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px] text-slate-600">1sulAaa2...</code></span>
              <span className="text-indigo-600 font-semibold cursor-pointer hover:underline">드라이브 설정</span>
            </div>
          </div>

          {/* ③ 3사분면 - 시간표 / 수업실 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2">
                <Clock className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-800 text-base">③ 시간표 / 수업실</h3>
              </div>
              <div className="flex items-center space-x-2">
                <div className="bg-slate-100 p-0.5 rounded-md flex text-xs font-semibold">
                  <button
                    onClick={() => setSelectedView("TEACHER")}
                    className={`px-2.5 py-1 rounded ${selectedView === "TEACHER" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600"}`}
                  >
                    교사별
                  </button>
                  <button
                    onClick={() => setSelectedView("CLASS")}
                    className={`px-2.5 py-1 rounded ${selectedView === "CLASS" ? "bg-white text-emerald-700 shadow-sm" : "text-slate-600"}`}
                  >
                    학급별
                  </button>
                </div>
                {selectedView === "TEACHER" ? (
                  <select
                    value={selectedTeacher}
                    onChange={(e) => setSelectedTeacher(e.target.value)}
                    className="text-xs bg-slate-100 border border-slate-200 rounded px-2 py-1 font-medium focus:outline-none"
                  >
                    <option value="홍길동">홍길동 선생님</option>
                    <option value="김철수">김철수 선생님</option>
                  </select>
                ) : (
                  <select
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    className="text-xs bg-slate-100 border border-slate-200 rounded px-2 py-1 font-medium focus:outline-none"
                  >
                    <option value="3학년 2반">3학년 2반</option>
                    <option value="3학년 1반">3학년 1반</option>
                  </select>
                )}
              </div>
            </div>

            <div className="space-y-2.5 flex-1">
              {data?.today_timetables.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center p-3 rounded-lg border border-slate-100 bg-slate-50 hover:bg-emerald-50/50 hover:border-emerald-200 transition justify-between"
                >
                  <div className="flex items-center space-x-3">
                    <span className="w-7 h-7 rounded-full bg-emerald-100 text-emerald-800 font-bold text-xs flex items-center justify-center">
                      {item.period}
                    </span>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-bold text-slate-800">{item.subject_name}</span>
                        {item.grade_number > 0 && (
                          <span className="text-xs text-slate-500 font-medium">({item.grade_number}-{item.class_number})</span>
                        )}
                        <span className="text-xs text-slate-400">· {item.teacher_name}</span>
                      </div>
                      <div className="flex items-center space-x-2 text-[11px] text-slate-500 mt-0.5">
                        {item.room_name && <span>교실: {item.room_name}</span>}
                        {item.practice_room_name && (
                          <span className="text-emerald-700 font-semibold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            실습실: {item.practice_room_name}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-slate-400">{item.lesson_type}</span>
                </div>
              ))}
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 text-xs text-slate-500 flex justify-between">
              <span>오늘 화요일 시간표 기준</span>
              <button className="text-emerald-700 font-semibold hover:underline">전체 주간 시간표</button>
            </div>
          </div>

          {/* ④ 4사분면 - 교직원 메시지 */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-5 flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
              <div className="flex items-center space-x-2">
                <MessageSquare className="w-5 h-5 text-amber-600" />
                <h3 className="font-bold text-slate-800 text-base">④ 교직원 메시지</h3>
              </div>
              <div className="flex items-center space-x-2">
                <div className="bg-slate-100 p-0.5 rounded-md flex text-xs font-semibold">
                  <button className="px-2 py-0.5 bg-white text-amber-700 rounded shadow-sm">전체</button>
                  <button className="px-2 py-0.5 text-slate-600">부서</button>
                  <button className="px-2 py-0.5 text-slate-600">개인</button>
                </div>
                <button className="text-xs px-2 py-1 bg-amber-50 hover:bg-amber-100 text-amber-800 rounded font-semibold transition">
                  메시지 작성
                </button>
              </div>
            </div>

            <div className="space-y-3 flex-1 overflow-y-auto">
              {data?.recent_messages.map((msg) => (
                <div
                  key={msg.id}
                  className="p-3 rounded-lg border border-slate-100 bg-slate-50 hover:bg-amber-50/50 hover:border-amber-200 transition"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center space-x-1.5">
                      <span className="text-xs font-bold text-slate-800">{msg.sender_name} 선생님</span>
                      {msg.title && (
                        <span className="text-xs text-amber-800 font-semibold bg-amber-100/70 px-1.5 py-0.5 rounded">
                          {msg.title}
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-400">{msg.created_at}</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed">{msg.content}</p>
                </div>
              ))}
            </div>

            <div className="pt-3 mt-3 border-t border-slate-100 text-xs text-slate-500 flex justify-between">
              <span>안읽은 공지 1건</span>
              <button className="text-amber-700 font-semibold hover:underline">교직원 연락망 보기</button>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
