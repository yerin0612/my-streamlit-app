
import streamlit as st
from openai import OpenAI

# OPENAI_API_KEY 환경변수가 설정되어 있어야 합니다.
client = OpenAI()

st.set_page_config(
    page_title="텍스트 음성 변환 서비스",
    page_icon="🔊"
)
st.title("텍스트 음성 변환 서비스")

text = st.text_area(
    "읽을 텍스트를 입력하세요",
    "안녕하세요. OpenAI 텍스트 음성 변환 실습입니다."
)

if st.button("변환"):
    if not text.strip():
        st.warning("읽을 텍스트를 입력해 주세요.")
    else:
        with st.spinner("음성을 생성하고 있습니다..."):
            speech = client.audio.speech.create(
                model="gpt-4o-mini-tts",
                voice="shimmer",
                input=text
            )

        st.success("변환이 완료되었습니다.")
        st.markdown("### 🔊 음성 재생")
        st.audio(speech.content, format="audio/mp3")
