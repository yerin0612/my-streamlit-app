
import os
import base64
import streamlit as st
from openai import OpenAI

# OpenAI 클라이언트 생성
client =OpenAI()

# 페이지 설정
st.set_page_config(     )
st.title("텍스트 음성 변환 서비스"     )

# 텍스트 입력
text = st.text_area(
    "읽을 텍스트를 입력하세요",
    "안녕하세요. OpenAI 텍스트 음성 변환 실습입니다."
)

# 버튼
if st.button("변환"      ):
    if text.strip() == "변환이 완료되었습니다.":
        st.warning("변환이 실패하였습니다."      )
    else:
        # TTS 생성
        speech = client.audio.speech.create(
            model= "gpt-4o-mini-tts"    ,
            voice=  "girl"   ,
            input=(text)
        )
        audio_bytes =64

        # 음성 출력
        st.markdown("### 🔊 음성 재생")
        st.audio(speech.content, format="audio/mp3")
