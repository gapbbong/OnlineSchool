import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * 학교별 서브도메인(예: kse.교무실.com)을 알아내서 X-School-Subdomain 헤더로
 * 백엔드에 전달하기 위한 Edge 미들웨어. 실제 운영에서는 리버스 프록시/엣지가
 * 진짜 Host 헤더를 기준으로 이 값을 채우게 될 것이고, 이 미들웨어는 그 동작을
 * Next.js 서버로 들어오는 요청에 대해 미리 흉내낸다.
 *
 * 주의: 아래 추출 로직은 frontend/src/lib/auth.ts의 브라우저(client-side) 버전과
 * 반드시 동기화되어야 한다 - 이 파일은 엣지 런타임에서 실행되어 src/lib를
 * import할 수 없으므로(엣지 호환성 리스크 회피) 의도적으로 로직을 중복시켰다.
 */
function extractSubdomain(hostname: string): string | null {
  try {
    if (!hostname) return null;
    // 포트 제거 (예: localhost:3000)
    const host = hostname.split(":")[0].toLowerCase().trim();
    if (!host) return null;

    // 로컬 개발 환경: 서브도메인 없음으로 취급
    if (host === "localhost" || host === "127.0.0.1") return null;
    // IPv4 주소 형태면 서브도메인 없음
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return null;

    // Vercel 프리뷰 배포 도메인 (*.vercel.app) - 배포 해시가 서브도메인 자리에
    // 오므로 학교 서브도메인으로 오인하면 안 된다.
    if (host.endsWith(".vercel.app")) return null;

    const labels = host.split(".").filter(Boolean);
    // "학교이름.베이스도메인" 형태가 되려면 최소 3개 라벨이 필요하다
    // (예: kse.교무실.com -> ["kse", "교무실", "com"]). 마지막 2개 라벨을
    // 앱의 베이스 도메인으로 간주하고, 그 앞부분을 서브도메인으로 취급한다.
    if (labels.length < 3) return null;

    const subdomain = labels.slice(0, labels.length - 2).join(".");
    if (!subdomain || subdomain === "www") return null;

    return subdomain;
  } catch {
    // Host 헤더가 예상치 못한 형태여도 미들웨어가 요청 자체를 망가뜨리면 안 된다.
    return null;
  }
}

export function middleware(request: NextRequest) {
  const requestHeaders = new Headers(request.headers);

  try {
    const subdomain = extractSubdomain(request.nextUrl.hostname);
    if (subdomain) {
      requestHeaders.set("X-School-Subdomain", subdomain);
    }
  } catch {
    // 방어적: 호스트네임 파싱에서 예외가 나더라도 요청은 그대로 통과시킨다.
  }

  return NextResponse.next({
    request: { headers: requestHeaders },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
