// 배포 학교마다 백엔드 주소가 달라질 수 있으므로 빌드 시점 환경변수로 주입한다.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

/**
 * 브라우저의 window.location.hostname에서 학교 서브도메인을 추출한다.
 * 미들웨어(middleware.ts)가 붙이는 X-School-Subdomain 헤더는 Next.js 서버로
 * 가는 요청에만 적용되므로, 브라우저가 백엔드(API_BASE_URL)로 직접 보내는
 * fetch에는 별도로 이 헤더를 붙여줘야 한다.
 *
 * 주의: 이 로직은 middleware.ts의 extractSubdomain()과 반드시 동기화되어야
 * 한다 - middleware.ts는 엣지 런타임에서 실행되어 이 파일을 import할 수 없으므로
 * (엣지 호환성 리스크 회피 목적) 의도적으로 중복시켰다. 둘 중 하나를 고치면
 * 다른 쪽도 같이 고쳐야 한다.
 */
export function getBrowserSchoolSubdomain(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const hostname = window.location.hostname;
    if (!hostname) return null;
    const host = hostname.toLowerCase().trim();

    if (host === "localhost" || host === "127.0.0.1") return null;
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null;
    if (host.endsWith(".vercel.app")) return null;

    const labels = host.split(".").filter(Boolean);
    if (labels.length < 3) return null;

    const subdomain = labels.slice(0, labels.length - 2).join(".");
    if (!subdomain || subdomain === "www") return null;

    return subdomain;
  } catch {
    return null;
  }
}
