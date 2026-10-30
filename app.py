
import streamlit as st
from openai import OpenAI

# OPENAI_API_KEY 환경변수가 설정되어 있어야 합니다.
client = OpenAI()

st.set_page_config(page_title="한영 번역기", page_icon="🌐")
st.title("한영 번역기")
st.write("한글 문장을 자연스러운 영어로 번역해 드립니다.")

korean_text = st.text_area(
    "번역할 한글 문장을 입력하세요.",
    height=150,
    placeholder="예: 인공지능은 우리의 일상과 업무 방식을 빠르게 변화시키고 있습니다."
)

if st.button("번역"):
    if not korean_text.strip():
        st.warning("번역할 문장을 입력해 주세요.")
    else:
        with st.spinner("번역 중입니다..."):
            sys_role = """
            당신은 전문 번역가입니다.
            사용자가 입력한 한국어 문장을 의미와 문맥을 살려 자연스러운 영어로 번역하세요.
            번역문만 출력하고, 별도의 설명이나 따옴표는 추가하지 마세요.
            """

            prompt = f"""
            다음 문장을 영어로 번역하세요.

            TEXT:
            {korean_text}
            """

            response = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": sys_role},
                    {"role": "user", "content": prompt}
                ]
            )

            translated_text = response.output_text

            st.subheader("영어 번역 결과")
            st.success(translated_text)
