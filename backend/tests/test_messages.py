import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_direct_message_is_private_to_sender_and_recipient(client):
    hong = await auth_headers("hong@kse.hs.kr")
    kim = await auth_headers("kim@kse.hs.kr")
    admin = await auth_headers("platform-admin@kse.hs.kr")

    # 김철수의 teacher_id 확인 (수신자 지정용)
    me_res = await client.get("/api/v1/auth/me", headers=kim)
    kim_teacher_id = me_res.json()["teacher_id"]

    send_res = await client.post(
        "/api/v1/messages",
        json={"msg_type": "DIRECT", "recipient_ids": [kim_teacher_id], "content": "3시에 협의실에서 뵙시다."},
        headers=hong,
    )
    assert send_res.status_code == 201

    # 수신자는 받은 메시지함에서 볼 수 있다.
    inbox_res = await client.get("/api/v1/messages?box=inbox", headers=kim)
    assert any(m["content"] == "3시에 협의실에서 뵙시다." for m in inbox_res.json())

    # 발신자는 보낸 메시지함에서 볼 수 있다.
    sent_res = await client.get("/api/v1/messages?box=sent", headers=hong)
    assert any(m["content"] == "3시에 협의실에서 뵙시다." for m in sent_res.json())

    # 이 대화와 무관한 제3자(관리자 포함)는 받은/보낸 어느 쪽에서도 보이지 않는다 - 진짜 비공개.
    admin_inbox = await client.get("/api/v1/messages?box=inbox", headers=admin)
    admin_sent = await client.get("/api/v1/messages?box=sent", headers=admin)
    assert all(m["content"] != "3시에 협의실에서 뵙시다." for m in admin_inbox.json())
    assert all(m["content"] != "3시에 협의실에서 뵙시다." for m in admin_sent.json())


@pytest.mark.asyncio
async def test_announcement_reaches_all_staff_and_mark_read(client):
    hong = await auth_headers("hong@kse.hs.kr")
    kim = await auth_headers("kim@kse.hs.kr")

    send_res = await client.post(
        "/api/v1/messages",
        json={"msg_type": "ANNOUNCEMENT", "title": "전체공지", "content": "내일 휴업입니다."},
        headers=hong,
    )
    assert send_res.status_code == 201

    inbox_res = await client.get("/api/v1/messages?box=inbox", headers=kim)
    matched = [m for m in inbox_res.json() if m["content"] == "내일 휴업입니다."]
    assert len(matched) == 1
    assert matched[0]["is_read"] is False

    read_res = await client.post(f"/api/v1/messages/{matched[0]['id']}/read", headers=kim)
    assert read_res.status_code == 204

    inbox_after = await client.get("/api/v1/messages?box=inbox", headers=kim)
    matched_after = next(m for m in inbox_after.json() if m["id"] == matched[0]["id"])
    assert matched_after["is_read"] is True


@pytest.mark.asyncio
async def test_message_can_link_task_and_timetable(client):
    hong = await auth_headers("hong@kse.hs.kr")

    task_res = await client.post(
        "/api/v1/tasks",
        json={"title": "링크테스트업무", "start_datetime": "2026-09-24T09:00:00"},
        headers=hong,
    )
    task_id = task_res.json()["id"]

    send_res = await client.post(
        "/api/v1/messages",
        json={"msg_type": "ANNOUNCEMENT", "content": "이 업무 확인해주세요.", "linked_task_id": task_id},
        headers=hong,
    )
    assert send_res.status_code == 201
    body = send_res.json()
    assert body["linked_task"]["id"] == task_id
    assert body["linked_task"]["title"] == "링크테스트업무"


@pytest.mark.asyncio
async def test_dashboard_message_preview_does_not_leak_direct_messages(client):
    """/dashboard의 4사분면 미리보기는 school_id로만 필터링해 학교 전체 최신 메시지를 보여주면
    안 된다 - 그러면 DIRECT(개인 쪽지)가 무관한 열람자에게 노출되는 개인정보 유출이 된다."""
    hong = await auth_headers("hong@kse.hs.kr")
    kim = await auth_headers("kim@kse.hs.kr")
    admin = await auth_headers("platform-admin@kse.hs.kr")

    me_res = await client.get("/api/v1/auth/me", headers=kim)
    kim_teacher_id = me_res.json()["teacher_id"]

    send_res = await client.post(
        "/api/v1/messages",
        json={"msg_type": "DIRECT", "recipient_ids": [kim_teacher_id], "content": "대시보드유출테스트비밀쪽지"},
        headers=hong,
    )
    assert send_res.status_code == 201

    # 수신자 본인은 대시보드 미리보기에서 자기 쪽지를 볼 수 있다.
    kim_dash = await client.get("/api/v1/dashboard", headers=kim)
    assert any(m["content"] == "대시보드유출테스트비밀쪽지" for m in kim_dash.json()["recent_messages"])

    # 이 대화와 무관한 제3자(관리자 포함)의 대시보드 미리보기에는 절대 노출되지 않는다.
    admin_dash = await client.get("/api/v1/dashboard", headers=admin)
    assert all(m["content"] != "대시보드유출테스트비밀쪽지" for m in admin_dash.json()["recent_messages"])

    # 비로그인 상태의 대시보드 미리보기에도 노출되지 않는다.
    anon_dash = await client.get("/api/v1/dashboard")
    assert all(m["content"] != "대시보드유출테스트비밀쪽지" for m in anon_dash.json()["recent_messages"])


@pytest.mark.asyncio
async def test_department_message_requires_target_and_direct_requires_recipients(client):
    hong = await auth_headers("hong@kse.hs.kr")

    missing_dept = await client.post(
        "/api/v1/messages", json={"msg_type": "DEPARTMENT", "content": "부서 공지"}, headers=hong
    )
    assert missing_dept.status_code == 422

    missing_recipients = await client.post(
        "/api/v1/messages", json={"msg_type": "DIRECT", "content": "쪽지"}, headers=hong
    )
    assert missing_recipients.status_code == 422
