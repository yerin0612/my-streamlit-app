import smtplib
from datetime import date
from email.message import EmailMessage
from email.policy import SMTP

import os, base64, json, requests

import streamlit as st
from openai import OpenAI


# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(page_title="AI비서 에이블", page_icon="🎙️")
st.title("🎙️ AI비서 에이블")
st.write("회의록과 음성 요청을 입력하면 회의 요약과 담당 업무를 음성으로 알려드려요.")


# ── 세션 상태 초기화 ────────────────────────────────────
if "schedules" not in st.session_state:
    st.session_state.schedules = []


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
            st.session_state.schedules.append({
                "date": schedule_date,
                "title": schedule_title.strip()
            })
            st.success("일정을 추가했어요.")
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
                if st.button(
                    "삭제",
                    key=f"delete_{selected_month}_{i}"
                ):
                    st.session_state.schedules.remove(item)
                    st.rerun()
    else:
        st.caption("등록된 일정이 없어요.")


# ── 회의록 및 요청 입력 ─────────────────────────────────
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
    placeholder="예: 미팅 내용을 요약하고, 나에게 배정된 업무를 자세히 알려줘."
)


# ── 이메일 설정 ─────────────────────────────────────────
send_email_option = st.checkbox("결과를 이메일로도 받기")
recipient = st.text_input(
    "받는 사람 이메일",
    value="yerin990@gmail.com",
    disabled=not send_email_option
)


# ── 요약 버튼 ───────────────────────────────────────────
if st.button("요약하고 음성으로 듣기", type="primary"):
    if meeting_file is None:
        st.error("회의록 파일을 먼저 올려주세요.")
        st.stop()

    request_text = typed_request.strip()

    # 음성 파일이 있으면 음성을 텍스트로 변환
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
        st.error("음성 파일을 올리거나 요청 내용을 직접 입력해주세요.")
        st.stop()

    # 업로드한 회의록 파일 읽기
    try:
        meeting_text = meeting_file.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        st.error("회의록 파일을 UTF-8 형식으로 저장한 뒤 다시 올려주세요.")
        st.stop()

    # 회의록을 바탕으로 답변 생성
    try:
        with st.spinner("회의 내용을 정리하고 있어요..."):
            response = client.responses.create(
                model="gpt-4o-mini",
                instructions=(
                    "회의 내용을 정리하는 개인 비서입니다. "
                    "회의록에 없는 내용은 추측하지 마세요. "
                    "반드시 아래 JSON 형식으로만 답하세요. "
                    '{"summary":"회의 요약과 담당 업무",'
                    '"schedules":[{"date":"YYYY-MM-DD","title":"일정 이름"}]} '
                    "날짜가 확실하지 않은 일정은 schedules에 넣지 마세요."
                ),
                input=f"""
[김 대리의 요청]
{request_text}

[회의록]
{meeting_text}
"""
            )
            result = json.loads(response.output_text)
            answer = result["summary"]
            extracted_schedules = result["schedules"]
        added_count = 0

        for item in extracted_schedules:
            try:
                schedule_date = date.fromisoformat(item["date"])
                schedule_title = item["title"].strip()

                if schedule_title:
                    new_schedule = {
                        "date": schedule_date,
                        "title": schedule_title
                    }

                    # 같은 날짜와 일정 이름이 이미 있으면 중복 추가하지 않기
                    if new_schedule not in st.session_state.schedules:
                        st.session_state.schedules.append(new_schedule)
                        added_count += 1

            except (KeyError, ValueError, TypeError):
                continue

        if added_count:
            st.success(f"회의록에서 일정 {added_count}개를 추가했어요.")

        st.subheader("회의 요약 및 담당 업무")
        st.write(answer)

    except Exception as e:
        st.error(f"회의 내용 정리에 실패했어요: {e}")
        st.stop()

    # 답변을 음성으로 변환
    audio_bytes = None

    try:
        with st.spinner("답변 음성을 만들고 있어요..."):
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="alloy",
                input=answer
            )
            audio_bytes = speech.content

        st.subheader("에이블의 음성 답변")
        st.audio(audio_bytes, format="audio/mpeg")

        st.download_button(
            "음성 파일 다운로드",
            data=audio_bytes,
            file_name="회의요약.mp3",
            mime="audio/mpeg"
        )

    except Exception as e:
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
