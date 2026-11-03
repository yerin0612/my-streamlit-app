import os
import smtplib
import streamlit as st
from email.message import EmailMessage
from email.policy import SMTP
from openai import OpenAI

st.set_page_config(page_title="에이블 회의 비서", page_icon="🎙️")
st.title("🎙️ 에이블 회의 비서")
st.write("회의록과 요청 음성을 올리면 요약과 담당 업무를 음성으로 알려드려요.")

client = OpenAI()  # 실행 셀에서 설정한 OPENAI_API_KEY 사용

meeting_file = st.file_uploader("회의록 파일", type=["txt"])
audio_file = st.file_uploader("요청 음성 파일", type=["m4a", "mp3", "wav", "webm"])
typed_request = st.text_area("또는 요청 내용을 직접 입력하세요")

send_email_option = st.checkbox("결과를 이메일로도 받기")
recipient = st.text_input("받는 사람 이메일", value="yerin990@gmail.com")

if st.button("요약하고 음성으로 듣기", type="primary"):
    if meeting_file is None:
        st.error("회의록 파일을 올려주세요.")
        st.stop()

    meeting_text = meeting_file.getvalue().decode("utf-8-sig")
    request_text = typed_request.strip()

    if audio_file is not None:
        with st.spinner("음성을 텍스트로 바꾸는 중..."):
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=audio_file
            )
            request_text = (request_text + "\n" + transcript.text).strip()

        st.subheader("음성에서 추출한 요청")
        st.write(transcript.text)

    if not request_text:
        st.error("요청 음성을 올리거나 요청 내용을 입력해주세요.")
        st.stop()

    with st.spinner("회의 내용을 정리하는 중..."):
        response = client.responses.create(
            model="gpt-4o-mini",
            instructions=(
                "당신은 김 대리의 개인 비서 에이블입니다. "
                "회의 내용을 요약하고, 김 대리에게 배정된 업무와 기한을 자세히 정리하세요. "
                "회의록에 없는 내용은 추측하지 마세요."
            ),
            input=f"""
[요청]
{request_text}

[회의록]
{meeting_text}
"""
        )
        answer = response.output_text

    with st.spinner("답변 음성을 만드는 중..."):
        speech_response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=answer
        )
        audio_bytes = speech_response.content

    st.subheader("에이블의 음성 답변")
    st.audio(audio_bytes, format="audio/mpeg")
    st.download_button(
        "음성 파일 다운로드",
        data=audio_bytes,
        file_name="회의요약.mp3",
        mime="audio/mpeg"
    )

    if send_email_option:
        sender = os.getenv("GMAIL_ADDRESS")
        app_password = os.getenv("GMAIL_APP_PASSWORD")

        if not sender or not app_password:
            st.error("이메일 발송용 Gmail Secret이 설정되지 않았어요.")
        else:
            try:
                message = EmailMessage(policy=SMTP)
                message["Subject"] = "미팅 내용 요약 및 담당 업무"
                message["From"] = sender
                message["To"] = recipient
                message.set_content(answer, charset="utf-8")

                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                    server.login(sender, app_password)
                    server.sendmail(sender, [recipient], message.as_bytes())

                st.success(f"{recipient} 주소로 이메일을 보냈어요.")
            except Exception as e:
                st.error(f"이메일 발송에 실패했어요: {e}")
