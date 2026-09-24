"use client";

import React from "react";

const SIZE_MAP = {
  xs: "h-3.5 w-3.5 border-[2px]",
  sm: "h-5 w-5 border-2",
  md: "h-8 w-8 border-[3px]",
  lg: "h-12 w-12 border-4",
} as const;

const TONE_MAP = {
  primary: "border-sky-200 border-t-sky-600",
  neutral: "border-slate-200 border-t-slate-500",
  onDark: "border-white/30 border-t-white",
} as const;

interface SpinnerProps {
  size?: keyof typeof SIZE_MAP;
  tone?: keyof typeof TONE_MAP;
  className?: string;
  label?: string;
}

/** 앱 전체에서 통일된 크기/색상으로 쓰는 로딩 스피너. */
export function Spinner({ size = "sm", tone = "primary", className = "", label }: SpinnerProps) {
  return (
    <span className="inline-flex items-center gap-2" role="status" aria-live="polite">
      <span
        className={`inline-block animate-spin rounded-full ${SIZE_MAP[size]} ${TONE_MAP[tone]} ${className}`}
      />
      {label && <span className="text-sm text-slate-500">{label}</span>}
      <span className="sr-only">{label || "로딩 중"}</span>
    </span>
  );
}

/** 패널/카드 내부가 비어있는 동안 중앙에 표시하는 로딩 상태. */
export function PanelLoading({ label = "불러오는 중...", minHeight = "min-h-[160px]" }: { label?: string; minHeight?: string }) {
  return (
    <div className={`flex ${minHeight} w-full flex-col items-center justify-center gap-3 text-slate-400`}>
      <Spinner size="md" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

/** 페이지 전체 초기 로딩(대시보드 첫 진입 등)에 쓰는 풀스크린 로딩 상태. */
export function PageLoading({ label = "불러오는 중..." }: { label?: string }) {
  return (
    <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-slate-50">
      <Spinner size="lg" />
      <p className="text-sm font-medium text-slate-500">{label}</p>
    </div>
  );
}

/** 버튼 안에서 쓰는 인라인 스피너 (텍스트와 같은 라인, 버튼 크기를 바꾸지 않음). */
export function ButtonSpinner({ tone = "onDark" }: { tone?: keyof typeof TONE_MAP }) {
  return <Spinner size="xs" tone={tone} className="mr-1.5 align-[-2px]" />;
}
