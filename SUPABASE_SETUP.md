# Supabase 연결 가이드 (최대한 쉽게)

이 프로젝트 백엔드는 SQLAlchemy(비동기)로 DB에 접속합니다. 지금은 로컬 SQLite 파일을 쓰고
있는데, `DATABASE_URL` 환경변수 하나만 Supabase 접속 주소로 바꾸면 코드 수정 없이 그대로
Supabase(Postgres)로 넘어갑니다.

## 1. 어떤 값이 필요한가 (딱 이것만 있으면 됨)

Supabase 대시보드에서 아래 **3가지**만 확인하면 됩니다.

1. **프로젝트 DB 비밀번호** — 프로젝트를 처음 만들 때 설정한 비밀번호
   (까먹었으면 `Project Settings → Database → Reset database password`에서 재설정 가능)
2. **접속 문자열(Connection string)** — 아래 경로에서 확인
   `Project Settings → Database → Connection string → URI`
   - 화면에 드롭다운으로 **Session pooler** / **Transaction pooler** / **Direct connection** 3종류가 나옵니다.
   - 우리 백엔드처럼 서버가 계속 켜져 있는 구조(서버리스 아님)는 **Session pooler**를 추천합니다.
     (Transaction pooler는 속도는 빠르지만 아래 "자주 겪는 에러"에 나온 문제가 생길 수 있어요)
3. 그게 전부입니다. Supabase의 `anon key`, `service_role key`는 **지금 구조에서는 필요 없습니다**
   (Supabase Auth/Storage 같은 부가 기능을 쓸 때만 필요 — 지금은 우리가 만든 자체 Google 로그인 +
   순수 Postgres 접속만 쓰기 때문에 DB 접속 문자열 하나면 충분합니다.)

## 2. 접속 문자열을 우리 코드에 맞게 바꾸기

Supabase가 보여주는 문자열은 이런 모양입니다.

```
postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres
```

여기서 딱 2군데만 바꾸면 됩니다.

1. `postgresql://` → `postgresql+asyncpg://` (SQLAlchemy가 비동기로 접속하려면 이 표기가 필요합니다)
2. `[YOUR-PASSWORD]` → 실제 비밀번호로 교체 (비밀번호에 `@`, `#`, `/` 같은 특수문자가 있으면
   URL 인코딩이 필요할 수 있어요 — 문제가 생기면 대시보드에서 비밀번호를 영문+숫자로 재설정하는 게 제일 간단합니다)

최종적으로 이런 모양이 되면 됩니다.

```
postgresql+asyncpg://postgres.xxxxxxxxxxxx:실제비밀번호@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres
```

## 3. 어디에 넣나요

`backend/.env` 파일(없으면 새로 생성, `backend/.env.example`을 복사해서 시작하면 편합니다)에
아래처럼 한 줄만 넣으면 됩니다.

```env
DATABASE_URL=postgresql+asyncpg://postgres.xxxxxxxxxxxx:실제비밀번호@aws-0-ap-northeast-2.pooler.supabase.com:5432/postgres
```

`.env` 파일은 `.gitignore`에 이미 포함되어 있어서 깃허브에 올라가지 않습니다 (비밀번호가 코드에
박히지 않도록 원래 이렇게 설계되어 있어요).

배포 환경(예: Render, Railway, Vercel 등)에 올릴 때는 그 플랫폼의 "환경변수(Environment
Variables)" 설정 화면에 `DATABASE_URL` 키로 동일한 값을 넣어주면 됩니다.

## 4. 필요한 패키지 설치

Postgres용 비동기 드라이버(`asyncpg`)를 이미 `backend/requirements.txt`에 추가해뒀습니다.
서버 켤 때 아래 한 번만 실행하면 됩니다.

```bash
cd backend
pip install -r requirements.txt
python -m app.init_db   # 테이블 생성 + 샘플 데이터 시드 (최초 1회, Supabase DB가 비어있을 때)
```

## 5. 자주 겪는 에러

**"prepared statement ... already exists" 같은 에러가 뜰 때**
→ Transaction pooler(포트 6543)를 쓰면 발생할 수 있는 알려진 이슈입니다. 아래 둘 중 하나로 해결하세요.
- 가장 쉬운 방법: Connection string을 **Session pooler**(포트 5432)로 바꾸기
- 또는 `backend/app/core/database.py`의 `create_async_engine(...)` 호출에
  `connect_args={"statement_cache_size": 0}`를 추가 (Transaction pooler를 꼭 써야 할 때만)

**"SSL 관련 에러"가 뜰 때**
→ Supabase는 기본적으로 SSL 접속을 요구합니다. 위 Session pooler 문자열을 그대로 쓰면 보통
문제없이 됩니다. 그래도 안 되면 접속 문자열 끝에 `?ssl=require`를 붙여보세요.

## 6. 여러 학교(Multi-tenant)는 어떻게 되나요

지금 구조는 학교마다 별도 DB를 만드는 게 아니라, **Supabase 프로젝트(DB) 하나**를 모든 학교가
같이 쓰고 각 테이블에 있는 `school_id` 컬럼으로 학교별 데이터를 구분합니다. 그래서 학교가
늘어나도 `DATABASE_URL`을 여러 개 관리할 필요 없이 지금 이 설정 그대로 두면 됩니다
(신규 학교 추가는 `POST /api/v1/admin/schools` API 하나로 처리 — 별도 DB 설정 불필요).

## 체크리스트

- [ ] Supabase 프로젝트 생성 + DB 비밀번호 확인/재설정
- [ ] `Project Settings → Database → Connection string → URI`에서 **Session pooler** 문자열 복사
- [ ] `postgresql://` → `postgresql+asyncpg://`로 바꾸고 비밀번호 채워넣기
- [ ] `backend/.env`에 `DATABASE_URL=...`로 저장
- [ ] `pip install -r requirements.txt` 후 `python -m app.init_db` 1회 실행
- [ ] 배포 플랫폼에도 동일한 `DATABASE_URL` 환경변수 등록
