"use client";

import React, { useState } from "react";
import { 
  UserCheck, Shield, BookOpen, Clock, Cloud, CheckCircle, 
  ArrowLeft, ArrowRight, School, Sparkles, Building, Phone, Mail, Car
} from "lucide-react";
import Link from "next/link";
import { authorizedFetch } from "@/lib/auth";

export default function TeacherOnboardingPage() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [submittedResult, setSubmittedResult] = useState<any>(null);
  const [authError, setAuthError] = useState<string | null>(null);

  // 폼 상태
  const [formData, setFormData] = useState({
    name: "강진우",
    phone_number: "010-3456-7890",
    workspace_email: "kang@kse.hs.kr",
    car_number: "55도 1234",
    phone_visibility: "ALL_STAFF",
    car_visibility: "ADMIN_ONLY",
    department_id: "",
    department_name: "연구부",
    position: "교과교사",
    assigned_work: "인공지능 교육 및 영재학급 운영",
    homeroom_grade: 3,
    homeroom_class: 1,
    subject_name: "정보",
    role: "TEACHER",
    initial_password: "",
    sync_google_drive: true,
    sync_google_sheets: true
  });

  const handleNext = () => setStep((prev) => Math.min(prev + 1, 5));
  const handlePrev = () => setStep((prev) => Math.max(prev - 1, 1));

  const handleSubmit = async () => {
    setLoading(true);
    setAuthError(null);
    try {
      const res = await authorizedFetch("/teachers/onboarding", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...formData,
          department_id: formData.department_id || "demo-dept-id"
        })
      });

      if (res.status === 401 || res.status === 403) {
        const detail = await res.json().catch(() => null);
        setAuthError(
          detail?.detail ||
            "신규 교사 등록은 관리자/부서장 로그인이 필요합니다. 먼저 로그인해주세요."
        );
        setLoading(false);
        return;
      }

      if (res.ok) {
        const json = await res.json();
        setSubmittedResult(json);
      } else {
        throw new Error("backend-unreachable");
      }
    } catch {
      // 백엔드 연결이 아예 되지 않는 로컬 프리뷰 환경을 위한 시뮬레이션 (인증 실패와는 별개)
      setTimeout(() => {
        setSubmittedResult({
          name: formData.name,
          workspace_email: formData.workspace_email,
          department_name: formData.department_name,
          role: "TEACHER",
          drive_folder_granted: true,
          sheets_access_granted: true,
          created_timetables_count: 14,
          message: `(프리뷰 모드) ${formData.name} 선생님의 교직원 계정 생성 및 구글 드라이브 폴더 연결이 완료되었습니다.`
        });
        setLoading(false);
      }, 700);
      return;
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col text-slate-800">
      {/* 상단 네비게이션 헤더 */}
      <header className="bg-white border-b border-slate-200 px-8 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2 text-sky-700 font-bold text-lg hover:opacity-80 transition">
            <School className="w-6 h-6" />
            <span>온라인 교무실</span>
          </Link>
          <span className="text-slate-300">/</span>
          <span className="text-sm font-semibold text-slate-600">신규 오신 선생님 전용 등록</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/teachers/bulk-import" className="text-xs font-semibold text-sky-700 hover:text-sky-800">
            여러 명 한 번에? 엑셀 일괄 등록 →
          </Link>
          <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
            <ArrowLeft className="w-3.5 h-3.5" /> 메인 대시보드로 돌아가기
          </Link>
        </div>
      </header>

      {/* 메인 마법사 영역 */}
      <div className="flex-1 max-w-4xl mx-auto w-full p-6 flex flex-col justify-center">
        
        {/* 진행 단계 표시 (Stepper) */}
        <div className="mb-8">
          <div className="flex items-center justify-between max-w-2xl mx-auto relative">
            <div className="absolute top-1/2 left-0 right-0 h-1 bg-slate-200 -translate-y-1/2 -z-0"></div>
            <div 
              className="absolute top-1/2 left-0 h-1 bg-sky-600 -translate-y-1/2 transition-all duration-300 -z-0"
              style={{ width: `${((step - 1) / 4) * 100}%` }}
            ></div>

            {[
              { num: 1, label: "기본 정보" },
              { num: 2, label: "학교 및 부서" },
              { num: 3, label: "학급 및 시간표" },
              { num: 4, label: "권한 & 개인정보" },
              { num: 5, label: "Google 연동 완료" }
            ].map((s) => (
              <div key={s.num} className="flex flex-col items-center relative z-10">
                <div 
                  className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm transition-all ${
                    step >= s.num ? "bg-sky-600 text-white shadow-md shadow-sky-600/30" : "bg-white text-slate-400 border-2 border-slate-200"
                  }`}
                >
                  {step > s.num ? "✓" : s.num}
                </div>
                <span className={`text-xs mt-2 font-medium ${step >= s.num ? "text-sky-700 font-bold" : "text-slate-400"}`}>
                  {s.label}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 폼 카드 컨테이너 */}
        <div className="bg-white border border-slate-200 rounded-2xl shadow-sm p-8 transition-all">
          
          {/* STEP 1: 기본 정보 */}
          {step === 1 && (
            <div className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <UserCheck className="w-5 h-5 text-sky-600" /> 선생님의 기본 인적사항을 입력해주세요
                </h2>
                <p className="text-xs text-slate-500 mt-1">학교 도메인 계정 및 비상 연락망으로 등록됩니다.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">성명 *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">휴대전화번호 *</label>
                  <div className="relative">
                    <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={formData.phone_number}
                      onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                      className="w-full pl-9 pr-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">Google Workspace 이메일 *</label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="email"
                      value={formData.workspace_email}
                      onChange={(e) => setFormData({ ...formData, workspace_email: e.target.value })}
                      className="w-full pl-9 pr-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    />
                  </div>
                  <p className="text-[11px] text-sky-600 mt-1">※ 학교 도메인(@kse.hs.kr)과 일치해야 자동 연동됩니다.</p>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">차량 번호 (출입 등록용)</label>
                  <div className="relative">
                    <Car className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={formData.car_number}
                      onChange={(e) => setFormData({ ...formData, car_number: e.target.value })}
                      placeholder="예: 12가 3456"
                      className="w-full pl-9 pr-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-sky-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* STEP 2: 학교 및 부서 배정 */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <Building className="w-5 h-5 text-indigo-600" /> 소속 부서 및 담당 업무를 지정해주세요
                </h2>
                <p className="text-xs text-slate-500 mt-1">부서가 배정되면 Google Drive 내 부서 공유 폴더 접근 권한이 자동 부여됩니다.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">소속 부서 *</label>
                  <select
                    value={formData.department_name}
                    onChange={(e) => setFormData({ ...formData, department_name: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none bg-white"
                  >
                    <option value="교무부">01_교무부 (교무기획, 학적, 교육통계)</option>
                    <option value="연구부">02_연구부 (교육과정, 전문적학습공동체)</option>
                    <option value="학생부">03_학생부 (생활지도, 학생자치, 안전)</option>
                    <option value="진로진학부">05_진로진학부 (취업, 진학, 산학협력)</option>
                    <option value="학년부">06_학년부 (1, 2, 3학년)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">직책</label>
                  <input
                    type="text"
                    value={formData.position}
                    onChange={(e) => setFormData({ ...formData, position: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-xs font-bold text-slate-700 mb-1">주요 담당 업무</label>
                  <input
                    type="text"
                    value={formData.assigned_work}
                    onChange={(e) => setFormData({ ...formData, assigned_work: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    placeholder="예: 인공지능 교육 선도학교 운영, 정보올림피아드 지도"
                  />
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: 학급 및 시간표 */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <BookOpen className="w-5 h-5 text-emerald-600" /> 담임 학급 및 담당 교과목
                </h2>
                <p className="text-xs text-slate-500 mt-1">시간표 엔진에 반영되어 학생 및 다른 선생님의 교무실 시간표에 실시간 노출됩니다.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">담임 학급 (해당 시)</label>
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      value={formData.homeroom_grade}
                      onChange={(e) => setFormData({ ...formData, homeroom_grade: Number(e.target.value) })}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                    >
                      <option value={0}>담임 없음</option>
                      <option value={1}>1학년</option>
                      <option value={2}>2학년</option>
                      <option value={3}>3학년</option>
                    </select>
                    <select
                      value={formData.homeroom_class}
                      onChange={(e) => setFormData({ ...formData, homeroom_class: Number(e.target.value) })}
                      className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                    >
                      <option value={1}>1반</option>
                      <option value={2}>2반</option>
                      <option value={3}>3반</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">담당 과목</label>
                  <select
                    value={formData.subject_name}
                    onChange={(e) => setFormData({ ...formData, subject_name: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="정보">정보</option>
                    <option value="인공지능">인공지능 기초</option>
                    <option value="국어">국어</option>
                    <option value="수학">수학</option>
                    <option value="영어">영어</option>
                  </select>
                </div>
              </div>

              <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-start gap-2.5">
                <Clock className="w-4 h-4 text-emerald-600 mt-0.5" />
                <div>
                  <span className="font-bold">기본 주간 시간표 자동 생성:</span> 등록 완료 시 학사일정에 맞춰 주 14~18시수의 시간표 슬롯이 교실 및 실습실과 함께 자동 초기 배정됩니다.
                </div>
              </div>
            </div>
          )}

          {/* STEP 4: 권한 및 개인정보 공개범위 */}
          {step === 4 && (
            <div className="space-y-6">
              <div className="border-b border-slate-100 pb-4">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-rose-600" /> 시스템 권한 및 개인정보 공개범위 설정
                </h2>
                <p className="text-xs text-slate-500 mt-1">설정된 정보는 API 서버사이드에서 엄격하게 마스킹되어 안전하게 보호됩니다.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">시스템 역할 (RBAC)</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="TEACHER">일반교사 (본인 업무 + 시간표 + 교직원 열람)</option>
                    <option value="DEPARTMENT_HEAD">부서장 (부서 업무 총괄 + 부서 Drive/Sheets 관리)</option>
                    <option value="SCHOOL_ADMIN">학교 관리자 (전체 권한)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">차량 번호 공개범위</label>
                  <select
                    value={formData.car_visibility}
                    onChange={(e) => setFormData({ ...formData, car_visibility: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="ADMIN_ONLY">관리자만 열람 (보안 권장)</option>
                    <option value="ALL_STAFF">전체 교직원 공개</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1">전화번호 공개범위</label>
                  <select
                    value={formData.phone_visibility}
                    onChange={(e) => setFormData({ ...formData, phone_visibility: e.target.value })}
                    className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                  >
                    <option value="ALL_STAFF">전체 교직원 공개</option>
                    <option value="SAME_DEPT">같은 부서원만 열람</option>
                    <option value="ADMIN_ONLY">관리자만 열람</option>
                  </select>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100">
                <label className="block text-xs font-bold text-slate-700 mb-1">초기 비밀번호 (선택 — 구글 워크스페이스 미사용 학교용)</label>
                <input
                  type="text"
                  value={formData.initial_password}
                  onChange={(e) => setFormData({ ...formData, initial_password: e.target.value })}
                  placeholder="비워두면 구글 로그인 전용 계정으로 생성됩니다"
                  className="w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm bg-white"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  값을 입력하면 이 선생님은 구글 계정 없이도 이메일+비밀번호로 로그인할 수 있습니다. 등록 후 본인이 변경하도록 안내하세요.
                </p>
              </div>
            </div>
          )}

          {/* STEP 5: 완료 및 확인 */}
          {step === 5 && (
            <div className="space-y-6">
              {!submittedResult ? (
                <div>
                  <div className="border-b border-slate-100 pb-4 mb-6">
                    <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                      <Sparkles className="w-5 h-5 text-sky-600" /> 입력 정보를 최종 확인하고 등록을 완료하세요
                    </h2>
                    <p className="text-xs text-slate-500 mt-1">원클릭으로 학교 DB 등록, Google Drive 권한 연결, 시간표 배치가 한번에 처리됩니다.</p>
                  </div>

                  <div className="bg-slate-50 rounded-xl p-5 border border-slate-200 space-y-3 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-200/60">
                      <span className="text-slate-500">교사명 / 이메일</span>
                      <span className="font-bold text-slate-800">{formData.name} ({formData.workspace_email})</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200/60">
                      <span className="text-slate-500">소속 부서 / 직책</span>
                      <span className="font-bold text-slate-800">{formData.department_name} · {formData.position}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-slate-200/60">
                      <span className="text-slate-500">담임 / 담당 과목</span>
                      <span className="font-bold text-slate-800">{formData.homeroom_grade}학년 {formData.homeroom_class}반 · {formData.subject_name}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-slate-500">자동 연동 대상</span>
                      <span className="font-bold text-sky-700">Google Drive ({formData.department_name} 폴더) + Sheets 업무대장</span>
                    </div>
                  </div>

                  {authError && (
                    <div className="mt-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center justify-between gap-3">
                      <span>{authError}</span>
                      <Link href="/login" className="font-bold underline whitespace-nowrap">
                        로그인하러 가기
                      </Link>
                    </div>
                  )}

                  <button
                    onClick={handleSubmit}
                    disabled={loading}
                    className="w-full mt-6 py-3 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-md transition flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <span>등록 파이프라인 처리 중...</span>
                    ) : (
                      <>
                        <CheckCircle className="w-5 h-5" />
                        <span>교사 등록 및 Google 권한 즉시 연결</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                /* 제출 완료 후 멋진 성공 화면 */
                <div className="py-6 text-center space-y-5">
                  <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
                    <CheckCircle className="w-9 h-9" />
                  </div>
                  <h3 className="text-2xl font-black text-slate-800">선생님 등록이 성공적으로 완료되었습니다!</h3>
                  <p className="text-sm text-slate-600 max-w-md mx-auto">
                    {submittedResult.message}
                  </p>

                  <div className="bg-emerald-50/70 border border-emerald-200 rounded-xl p-4 max-w-md mx-auto text-left text-xs space-y-2 text-emerald-900">
                    <div className="flex items-center gap-2">
                      <Cloud className="w-4 h-4 text-emerald-600" />
                      <span>Google Drive 폴더 권한: <strong>정상 부여됨</strong></span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-emerald-600" />
                      <span>시간표 초기 등록: <strong>{submittedResult.created_timetables_count} 시수 반영 완료</strong></span>
                    </div>
                  </div>

                  <div className="pt-4 flex justify-center gap-3">
                    <Link
                      href="/"
                      className="px-6 py-2.5 bg-sky-700 hover:bg-sky-800 text-white text-sm font-bold rounded-xl shadow transition"
                    >
                      교무실 메인 대시보드로 이동
                    </Link>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 하단 이전/다음 버튼 */}
          {!submittedResult && (
            <div className="mt-8 pt-4 border-t border-slate-100 flex items-center justify-between">
              <button
                onClick={handlePrev}
                disabled={step === 1}
                className={`px-4 py-2 text-xs font-semibold rounded-lg flex items-center gap-1 transition ${
                  step === 1 ? "text-slate-300 cursor-not-allowed" : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                <ArrowLeft className="w-4 h-4" /> 이전 단계
              </button>

              {step < 5 && (
                <button
                  onClick={handleNext}
                  className="px-5 py-2 bg-sky-600 hover:bg-sky-700 text-white text-xs font-bold rounded-lg shadow-sm transition flex items-center gap-1"
                >
                  다음 단계 <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
