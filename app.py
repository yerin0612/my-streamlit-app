import json
import smtplib
from datetime import date
from email.message import EmailMessage
from email.policy import SMTP

import streamlit as st
from openai import OpenAI


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(page_title="AI비서 에이블", page_icon="🎙️")
st.title("🎙️ AI비서 에이블")
st.write("회의록과 음성 요청을 입력하면 회의 요약, 담당 업무, 일정을 정리해 드려요.")


# ── 세션 상태 초기화 ────────────────────────────────────
if "schedules" not in st.session_state:
    st.session_state.schedules = []

if "pending_schedules" not in st.session_state:
    st.session_state.pending_schedules = []

if "latest_result" not in st.session_state:
    st.session_state.latest_result = None

if "latest_audio" not in st.session_state:
    st.session_state.latest_audio = None


# ── OpenAI 클라이언트 ──────────────────────────────────
try:
    client = OpenAI()
except Exception as e:
    st.error(f"OpenAI API 키 설정을 확인해 주세요: {e}")
    st.stop()


# ── 사이드바: 일정 모음 ─────────────────────────────────
with st.sidebar:
    st.header("📅 일정 모음")

    schedule_date = st.date_input("날짜 선택", value=date.today())
    schedule_title = st.text_input("일정 이름")

    if st.button("일정 추가"):
        if schedule_title.strip():
            new_schedule = {
                "date": schedule_date,
                "title": schedule_title.strip()
            }

            if new_schedule not in st.session_state.schedules:
                st.session_state.schedules.append(new_schedule)

            st.rerun()
        else:
            st.warning("일정 이름을 입력해 주세요.")

    st.divider()

    # 저장된 일정이 있는 달과 이번 달을 월 목록으로 표시
    schedule_months = {
        item["date"].strftime("%Y-%m")
        for item in st.session_state.schedules
    }
    schedule_months.add(date.today().strftime("%Y-%m"))
    months = sorted(schedule_months, reverse=True)

    selected_month = st.selectbox("월별 일정 보기", months)
    st.subheader(f"🗓️ {selected_month} 일정")

    monthly_schedules = [
        item for item in st.session_state.schedules
        if item["date"].strftime("%Y-%m") == selected_month
    ]

    if monthly_schedules:
        for i, item in enumerate(
            sorted(monthly_schedules, key=lambda x: x["date"])
        ):
            col1, col2 = st.columns([4, 1])

            with col1:
                st.write(
                    f"**{item['date'].strftime('%m/%d')}** — {item['title']}"
                )

            with col2:
                if st.button("삭제", key=f"delete_{selected_month}_{i}"):
                    st.session_state.schedules.remove(item)
                    st.rerun()
    else:
        st.caption("등록된 일정이 없어요.")


# ── 회의록과 요청 입력 ──────────────────────────────────
meeting_file = st.file_uploader(
    "회의록 파일을 올려주세요",
    type=["txt"]
)

audio_file = st.file_uploader(
    "요청 음성 파일을 올려주세요",
    type=["m4a", "mp3", "wav", "webm"]
)

typed_request = st.text_area(
    "또는 요청 내용을 직접 입력하세요",
    placeholder="예: 회의 내용을 요약하고, 나에게 배정된 업무를 자세히 알려줘."
)


# ── 이메일 설정 ─────────────────────────────────────────
send_email_option = st.checkbox("결과를 이메일로도 받기")

recipient = st.text_input(
    "받는 사람 이메일",
    value="yerin990@gmail.com",
    disabled=not send_email_option
)


# ── 회의 처리 ───────────────────────────────────────────
if st.button("요약하고 음성으로 듣기", type="primary"):
    if meeting_file is None:
        st.error("회의록 파일을 먼저 올려주세요.")
        st.stop()

    request_text = typed_request.strip()

    # 음성 요청이 있으면 음성을 텍스트로 변환
    if audio_file is not None:
        try:
            with st.spinner("음성을 텍스트로 변환하고 있어요..."):
                transcript = client.audio.transcriptions.create(
                    model="gpt-4o-mini-transcribe",
                    file=audio_file
                )
                request_text = transcript.text.strip()

            st.subheader("음성에서 추출한 요청")
            st.write(request_text)

        except Exception as e:
            st.error(f"음성 변환에 실패했어요: {e}")
            st.stop()

    if not request_text:
        st.error("음성 파일을 올리거나 요청 내용을 직접 입력해 주세요.")
        st.stop()

    # 회의록 파일 읽기
    try:
        meeting_text = meeting_file.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        st.error("회의록 파일을 UTF-8 형식으로 저장한 뒤 다시 올려주세요.")
        st.stop()

    # AI에게 요청할 출력 형식
    instructions = """
당신은 김 대리의 개인 비서 에이블입니다.
회의록에 실제로 적힌 내용만 사용하고, 없는 내용은 추측하지 마세요.
반드시 JSON 객체만 출력하세요. JSON 앞뒤에 설명이나 마크다운을 붙이지 마세요.

summary에는 회의 목적과 전체 흐름을 3~5문장으로 설명하세요.
key_points에는 중요한 안건과 논의 내용을 항목별로 작성하세요.
decisions에는 회의에서 확정된 결정 사항을 작성하세요.
my_tasks에는 김 대리에게 배정된 업무만 넣으세요.
각 업무마다 task는 할 일, details는 구체적인 작업 내용,
deadline은 기한으로 작성하세요. 기한이 없으면 "미정"이라고 쓰세요.

회의록에 날짜가 명확하지 않은 일정도 schedules에 포함하세요.
날짜가 확정되어 있으면 date에 YYYY-MM-DD 형식으로 쓰세요.
날짜가 불확실하면 date에는 null을 쓰고 date_hint에 회의록의 날짜 표현을 쓰세요.
일정 이름은 title에 작성하세요.
해당 항목이 없으면 빈 배열을 사용하세요.

출력 예시:
{
  "summary": "회의 요약",
  "key_points": ["핵심 안건과 논의 내용"],
  "decisions": ["확정된 결정 사항"],
  "my_tasks": [
    {
      "task": "해야 할 일",
      "details": "구체적인 작업 내용",
      "deadline": "기한 또는 미정"
    }
  ],
  "schedules": [
    {
      "date": "2026-11-12 또는 null",
      "date_hint": "다음 주 중",
      "title": "일정 이름"
    }
  ]
}
"""

    try:
        with st.spinner("회의 내용을 정리하고 일정을 찾고 있어요..."):
            response = client.responses.create(
                model="gpt-4o-mini",
                instructions=instructions,
                input=f"""
                아래 내용을 분석하고 json 객체로만 답변해 주세요.
[김 대리의 요청]
{request_text}

[회의록]
{meeting_text}
""",
                text={"format": {"type": "json_object"}}
            )

        result_text = response.output_text

        if not result_text:
            st.error("AI가 정리 결과를 비워서 보냈어요. 다시 시도해 주세요.")
            st.stop()

        result = json.loads(result_text)

    except json.JSONDecodeError:
        st.error("AI 응답을 읽지 못했어요. 다시 시도해 주세요.")
        st.stop()
    except Exception as e:
        st.error(f"회의 내용 정리에 실패했어요: {e}")
        st.stop()

    # 일정 분류: 날짜가 있으면 자동 추가, 없으면 날짜 선택 대기
    added_count = 0
    pending = []

    for item in result.get("schedules", []):
        title = str(item.get("title", "")).strip()
        raw_date = item.get("date")

        if not title:
            continue

        if raw_date:
            try:
                schedule_date = date.fromisoformat(raw_date)
                new_schedule = {
                    "date": schedule_date,
                    "title": title
                }

                if new_schedule not in st.session_state.schedules:
                    st.session_state.schedules.append(new_schedule)
                    added_count += 1
            except (TypeError, ValueError):
                pending.append(item)
        else:
            pending.append(item)

    st.session_state.pending_schedules = pending
    st.session_state.latest_result = result

    if added_count:
        st.success(f"날짜가 확실한 일정 {added_count}개를 자동으로 추가했어요.")

    # 음성 답변 만들기
    answer_parts = []

    if result.get("summary"):
        answer_parts.append("회의 요약. " + result["summary"])

    if result.get("key_points"):
        answer_parts.append(
            "핵심 안건. " + " ".join(result["key_points"])
        )

    if result.get("decisions"):
        answer_parts.append(
            "결정 사항. " + " ".join(result["decisions"])
        )

    if result.get("my_tasks"):
        task_texts = []
        for task in result["my_tasks"]:
            task_texts.append(
                f"{task.get('task', '')}. "
                f"{task.get('details', '')}. "
                f"기한은 {task.get('deadline', '미정')}."
            )
        answer_parts.append("김 대리 담당 업무. " + " ".join(task_texts))

    answer = " ".join(answer_parts)

    if not answer.strip():
        answer = "회의록에서 요약할 내용을 찾지 못했어요."

    try:
        with st.spinner("답변 음성을 만들고 있어요..."):
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=answer
            )
            audio_bytes = speech.read()

        if audio_bytes:
            st.session_state.latest_audio = audio_bytes
        else:
            st.session_state.latest_audio = None
            st.warning("음성 데이터가 비어 있어요. 요약 내용은 확인할 수 있어요.")

    except Exception as e:
        st.session_state.latest_audio = None
        st.error(f"음성 생성에 실패했어요: {e}")

    # 이메일 발송
    if send_email_option:
        if not recipient.strip():
            st.warning("받는 사람 이메일을 입력해 주세요.")
        else:
            try:
                sender = st.secrets["GMAIL_ADDRESS"]
                app_password = st.secrets["GMAIL_APP_PASSWORD"]

                message = EmailMessage(policy=SMTP)
                message["Subject"] = "미팅 내용 요약 및 담당 업무"
                message["From"] = sender
                message["To"] = recipient.strip()
                message.set_content(answer, charset="utf-8")

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(sender, app_password)
                    server.sendmail(
                        sender,
                        [recipient.strip()],
                        message.as_bytes()
                    )

                st.success(f"{recipient.strip()} 주소로 이메일을 보냈어요.")

            except KeyError:
                st.error(
                    "이메일 설정이 없어요. Streamlit Secrets에 "
                    "GMAIL_ADDRESS와 GMAIL_APP_PASSWORD를 등록해 주세요."
                )
            except Exception as e:
                st.error(f"이메일 발송에 실패했어요: {e}")

    # 사이드바 일정과 결과를 갱신
    st.rerun()


# ── 날짜가 불확실한 일정: 직접 날짜 지정 ────────────────
if st.session_state.pending_schedules:
    st.subheader("📅 날짜를 확인할 일정")

    for i, item in enumerate(st.session_state.pending_schedules):
        title = item.get("title", "이름 없는 일정")
        date_hint = item.get("date_hint", "날짜 미정")

        st.write(f"**{title}** — 회의록 표현: {date_hint}")

        chosen_date = st.date_input(
            "이 일정의 날짜를 선택하세요",
            value=date.today(),
            key=f"pending_date_{i}"
        )

        if st.button("선택한 날짜로 추가", key=f"add_pending_{i}"):
            st.session_state.schedules.append({
                "date": chosen_date,
                "title": title
            })
            st.session_state.pending_schedules.pop(i)
            st.rerun()


# ── 요약 결과 표시 ──────────────────────────────────────
if st.session_state.latest_result:
    result = st.session_state.latest_result

    st.subheader("회의 요약")
    st.write(result.get("summary", ""))

    st.subheader("핵심 안건")
    key_points = result.get("key_points", [])
    if key_points:
        for point in key_points:
            st.write(f"- {point}")
    else:
        st.caption("정리된 핵심 안건이 없어요.")

    st.subheader("결정 사항")
    decisions = result.get("decisions", [])
    if decisions:
        for decision in decisions:
            st.write(f"- {decision}")
    else:
        st.caption("회의록에서 확정된 결정 사항을 찾지 못했어요.")

    st.subheader("김 대리 담당 업무")
    tasks = result.get("my_tasks", [])
    if tasks:
        for task in tasks:
            st.markdown(f"**할 일:** {task.get('task', '')}")
            st.write(f"**구체적인 내용:** {task.get('details', '')}")
            st.write(f"**기한:** {task.get('deadline', '미정')}")
    else:
        st.caption("회의록에서 김 대리 담당 업무를 찾지 못했어요.")

    if st.session_state.latest_audio:
        st.subheader("에이블의 음성 답변")
        st.audio(st.session_state.latest_audio, format="audio/mpeg")

        st.download_button(
            "음성 파일 다운로드",
            data=st.session_state.latest_audio,
            file_name="회의요약.mp3",
            mime="audio/mpeg"
        )
