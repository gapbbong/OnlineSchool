// 배포 학교마다 백엔드 주소가 달라질 수 있으므로 빌드 시점 환경변수로 주입한다.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
