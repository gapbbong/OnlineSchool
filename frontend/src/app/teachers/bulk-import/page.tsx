"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle, Download, School, Upload, XCircle } from "lucide-react";
import { authorizedFetch } from "@/lib/auth";
import { ButtonSpinner } from "@/components/Spinner";
import { logEvent } from "@/lib/analytics";

interface RowResult {
  row: number;
  name?: string | null;
  success: boolean;
  message?: string | null;
  error?: string | null;
}

interface BulkImportResponse {
  total_rows: number;
  succeeded: number;
  failed: number;
  results: RowResult[];
}

export default function BulkImportPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [downloading, setDownloading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BulkImportResponse | null>(null);

  async function handleDownloadTemplate() {
    setDownloading(true);
    setError(null);
    try {
      const res = await authorizedFetch("/teachers/onboarding/template");
      if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || "양식 다운로드에 실패했습니다. 로그인 상태를 확인해주세요.");
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "teacher_onboarding_template.xlsx";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "양식 다운로드 중 오류가 발생했습니다.");
    } finally {
      setDownloading(false);
    }
  }

  async function handleUpload() {
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setError("업로드할 엑셀 파일을 선택해주세요.");
      return;
    }
    setUploading(true);
    setError(null);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await authorizedFetch("/teachers/onboarding/bulk", { method: "POST", body: form });
      const data = await res.json().catch(() => null);
      if (!res.ok) {
        throw new Error(data?.detail || "일괄 등록에 실패했습니다.");
      }
      setResult(data as BulkImportResponse);
      logEvent("BULK_IMPORT", { succeeded: data.succeeded, failed: data.failed });
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드 중 오류가 발생했습니다.");
    } finally {
      setUploading(false);
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
          <span className="text-sm font-semibold text-slate-600">교사 엑셀 일괄 등록</span>
        </div>
        <Link href="/" className="text-xs font-medium text-slate-500 hover:text-slate-800 flex items-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> 메인 대시보드로 돌아가기
        </Link>
      </header>

      <div className="flex-1 max-w-3xl mx-auto w-full p-6 space-y-6">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">1. 양식 다운로드</h2>
            <p className="text-xs text-slate-500 mt-1">
              우리 학교의 실제 부서/과목 목록이 참고 시트로 포함된 엑셀 양식을 내려받습니다. (관리자/부서장 로그인 필요)
            </p>
          </div>
          <button
            onClick={handleDownloadTemplate}
            disabled={downloading}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 disabled:opacity-70 disabled:cursor-not-allowed text-slate-700 text-sm font-semibold rounded-lg transition"
          >
            {downloading ? <ButtonSpinner tone="neutral" /> : <Download className="w-4 h-4" />}
            {downloading ? "다운로드 중..." : "엑셀 양식 다운로드"}
          </button>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div>
            <h2 className="text-lg font-bold text-slate-800">2. 작성한 엑셀 업로드</h2>
            <p className="text-xs text-slate-500 mt-1">
              한 행이 잘못되어도(오탈자, 중복 이메일 등) 나머지 행은 정상적으로 등록되고, 결과가 행별로 표시됩니다.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xlsm"
              className="text-xs file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-sky-50 file:text-sky-700 file:font-semibold hover:file:bg-sky-100"
            />
            <button
              onClick={handleUpload}
              disabled={uploading}
              className="inline-flex items-center gap-2 px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-70 disabled:cursor-not-allowed text-white text-sm font-bold rounded-lg shadow-sm transition flex-shrink-0"
            >
              {uploading ? <ButtonSpinner /> : <Upload className="w-4 h-4" />}
              {uploading ? "처리 중..." : "일괄 등록 실행"}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-center justify-between gap-3">
            <span>{error}</span>
            <Link href="/login" className="font-bold underline whitespace-nowrap">
              로그인하러 가기
            </Link>
          </div>
        )}

        {result && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-800">처리 결과</h2>
              <div className="text-xs font-semibold flex gap-3">
                <span className="text-emerald-700">성공 {result.succeeded}건</span>
                <span className="text-rose-600">실패 {result.failed}건</span>
                <span className="text-slate-400">전체 {result.total_rows}건</span>
              </div>
            </div>
            <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
              {result.results.map((r) => (
                <div key={r.row} className="py-2 flex items-start gap-2 text-xs">
                  {r.success ? (
                    <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                  )}
                  <div>
                    <span className="font-semibold text-slate-700">{r.row}행 {r.name ? `· ${r.name}` : ""}</span>
                    <p className={r.success ? "text-slate-500" : "text-rose-600"}>{r.success ? r.message : r.error}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
