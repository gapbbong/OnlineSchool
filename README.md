# 🏫 온라인 교무실 (Online Faculty Hub)

> **"학교 업무의 시작점이자 올인원 업무 허브"**  
> 복잡한 교무 행정 업무, 다차원 시간표, Google Workspace(Drive / Sheets)를 한 화면에서 직관적으로 처리하는 차세대 학교 SaaS 플랫폼입니다.

---

## ✨ 핵심 기능 및 설계 원칙

1. **온라인 교무실 DB = Source of Truth**
   - 자체 관계형 DB를 데이터 원본으로 두고, Google Workspace(Drive, Sheets, Calendar)는 비동기 아웃박스 패턴으로 연동합니다.
   - 외부 Google API 지연이나 일시적 네트워크 단절 시에도 교무실 웹시스템은 중단 없이 100% 가동됩니다.
2. **도메인 및 드라이브 폴더 하드코딩 배제 (Multi-Tenant Architecture)**
   - `kse.hs.kr`, 드라이브 루트 ID(`1sulAaa2...`)는 코드에 하드코딩되지 않고 각 학교의 `SchoolSettings`에 저장되어 관리됩니다.
   - 향후 다른 학교(`abc.hs.kr`, `xyz.hs.kr` 등)도 독립된 데이터 공간으로 운영할 수 있습니다.
3. **4분할 반응형 대시보드 (메인 화면)**
   - **① 1사분면 (업무 캘린더)**: 오늘/주간 업무, 상태(완료/진행), 부서 태그, 마감시간
   - **② 2사분면 (자주 쓰는 바로가기)**: 교무자료실, 학교 Sheets, NEIS, Gmail, Google Calendar, Google Drive 링크
   - **③ 3사분면 (시간표 / 수업실)**: 교사별/학급별 전환 스위치, 과목/교실(302호)/실습실(컴퓨터실 B) 동시 표시
   - **④ 4사분면 (교직원 메시지)**: 전체/부서/개인 공지 및 쪽지
4. **"새로 오신 선생님" 전용 원스톱 온보딩 (`/teachers/onboarding`)**
   - 5단계 인터랙티브 마법사: 인적사항 → 부서/직책 → 담임/과목 → 권한/개인정보 공개범위 → 원클릭 자동 연동 (계정 생성, 시간표 배치, Google Drive 폴더 권한 부여)
5. **엄격한 개인정보 보호 및 서버측 RBAC 보안**
   - 차량번호, 휴대전화번호 등의 공개범위를 지정할 수 있으며, UI 숨김뿐만 아니라 API 서버 레벨에서 엄격히 마스킹됩니다.

---

## 🚀 빠른 시작 (Quick Start)

### 원클릭 실행 (추천)
프로젝트 루트의 [`start.bat`](file:///e:/OnlineSchool/start.bat) 파일을 더블클릭하면 백엔드와 프론트엔드가 동시에 실행됩니다.

### 수동 실행
**1. 백엔드 (FastAPI)**
```powershell
cd e:\OnlineSchool\backend
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```
- API Swagger 문서: `http://localhost:8000/docs`

**2. 프론트엔드 (Next.js 14)**
```powershell
cd e:\OnlineSchool\frontend
npm run dev
```
- 온라인 교무실 메인 대시보드: `http://localhost:3000`
- 신규 교사 온보딩 마법사: `http://localhost:3000/teachers/onboarding`
