
import os
import hashlib
from pathlib import Path

import streamlit as st
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter


# ─────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────
with st.sidebar:
    st.image("aivle_logo.png", width=170)
    st.caption("AIVLE School 학습 도우미")

CHROMA_DIR = "chroma_db"
COLLECTION = "aivle_docs"
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


# ─────────────────────────────────────────
# 디자인
# ─────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', 'Noto Sans KR', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at 10% 0%, rgba(42, 211, 190, .10), transparent 28%),
            #f7fafb;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e9fbf8 0%, #f7fbfc 100%);
        border-right: 1px solid #d8eeeb;
    }

    .hero {
        padding: 28px 30px;
        border-radius: 24px;
        color: white;
        background: linear-gradient(120deg, #123f4a 0%, #087f83 55%, #35c7b4 100%);
        box-shadow: 0 14px 35px rgba(8, 127, 131, .18);
        margin-bottom: 20px;
    }

    .hero-kicker {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: .12em;
        opacity: .82;
        text-transform: uppercase;
    }

    .hero h1 {
        margin: 8px 0 6px 0;
        font-size: 30px;
        font-weight: 800;
        color: white;
    }

    .hero p {
        margin: 0;
        font-size: 15px;
        opacity: .9;
    }

    .info-card {
        background: white;
        border: 1px solid #e5eeee;
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 16px rgba(22, 57, 63, .04);
        margin-bottom: 12px;
    }

    .small-label {
        color: #648084;
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .stChatMessage {
        border: 1px solid #e7eeee;
        border-radius: 16px;
        padding: 12px 14px;
        background: rgba(255,255,255,.85);
    }

    .stChatInput textarea {
        border-radius: 14px !important;
    }

    div.stButton > button {
        border-radius: 12px;
        font-weight: 700;
        border: 1px solid #cde7e3;
    }

    div.stButton > button:hover {
        border-color: #27b8a7;
        color: #087f83;
    }

    .footer-note {
        color: #82989b;
        font-size: 12px;
        text-align: center;
        padding: 22px 0 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────
# API 키 확인
# ─────────────────────────────────────────
def has_api_key():
    return bool(
        st.secrets.get("OPENAI_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
    )


# ─────────────────────────────────────────
# RAG 유틸리티
# ─────────────────────────────────────────
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


@st.cache_resource
def get_vectorstore():
    embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL)

    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embedding,
        persist_directory=CHROMA_DIR,
    )


@st.cache_resource
def get_chain():
    retriever = get_vectorstore().as_retriever(
        search_kwargs={"k": 3}
    )

    system_message = """
당신은 AIVLE School 학습 도우미입니다.

아래에 제공된 문서 내용을 우선 근거로 답변하세요.
문서에서 확인할 수 없는 내용은 사실처럼 만들어내지 말고,
"제공된 문서에서는 확인하기 어렵습니다"라고 말한 뒤 필요한 정보를 안내하세요.

답변은 한국어로 작성하고, 초보자도 이해할 수 있도록 설명하세요.
코드 질문에는 핵심 원인과 수정 예시를 함께 제시하세요.

[참고 문서]
{context}
"""

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", "{input}"),
        ]
    )

    llm = ChatOpenAI(
        model=CHAT_MODEL,
        temperature=0,
        streaming=True,
    )

    return (
        {
            "context": itemgetter("input") | retriever | format_docs,
            "input": itemgetter("input"),
        }
        | prompt
        | llm
        | StrOutputParser()
    )


def add_uploaded_file(uploaded_file):
    """업로드된 파일을 중복 저장하지 않고 Chroma에 추가."""
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    if file_hash in st.session_state.indexed_files:
        return False, "이미 추가한 파일이에요."

    try:
        from langchain_core.documents import Document

        text = file_bytes.decode("utf-8")
        docs = [
            Document(
                page_content=text,
                metadata={"source": uploaded_file.name},
            )
        ]

        embedding = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        vectorstore = get_vectorstore()
        vectorstore.add_documents(
            docs,
            ids=[file_hash],
        )

        st.session_state.indexed_files.add(file_hash)
        return True, "문서를 추가했어요."

    except UnicodeDecodeError:
        return False, "현재는 UTF-8 텍스트 파일만 업로드할 수 있어요."
    except Exception as e:
        return False, f"파일을 추가하지 못했어요: {e}"


# ─────────────────────────────────────────
# 세션 상태
# ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = set()


# ─────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📎 자료 추가")

    uploaded_file = st.file_uploader(
        "텍스트 문서 업로드",
        type=["txt", "md"],
        help="현재 예시는 TXT 또는 Markdown 문서를 지원합니다.",
    )

    if uploaded_file is not None:
        if st.button("문서를 지식 저장소에 추가", use_container_width=True):
            if not has_api_key():
                st.error("OPENAI_API_KEY를 먼저 등록해 주세요.")
            else:
                success, message = add_uploaded_file(uploaded_file)
                if success:
                    st.success(message)
                else:
                    st.warning(message)

    st.markdown("---")
    st.markdown("### ✨ 추천 질문")

    suggested_questions = [
        "이번 프로젝트에서 RAG가 어떤 역할을 하나요?",
        "문서 업로드 기능은 어떻게 구현하나요?",
        "Streamlit에서 대화 기록을 초기화하는 방법을 알려줘",
        "문서에 근거해 핵심 내용을 요약해줘",
    ]

    for question in suggested_questions:
        if st.button(question, use_container_width=True):
            st.session_state.pending_question = question

    st.markdown("---")
    if st.button("🗑️ 대화 내용 삭제", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pop("pending_question", None)
        st.rerun()


# ─────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">KT AIVLE SCHOOL · STUDY ASSISTANT</div>
        <h1>에이블에게 물어보세요 👋</h1>
        <p>수업 자료를 바탕으로 함께 설명해 드릴게요.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="info-card"><div class="small-label">답변 방식</div>'
        '<b>업로드한 문서 기반 RAG</b></div>',
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="info-card"><div class="small-label">도움 주제</div>'
        '<b>수업 개념 · 코드 · 프로젝트</b></div>',
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="info-card"><div class="small-label">대화 기록</div>'
        f'<b>{len(st.session_state.messages) // 2}개 질문</b></div>',
        unsafe_allow_html=True,
    )

if not Path(CHROMA_DIR).exists():
    st.warning(
        f"`{CHROMA_DIR}` 폴더를 찾지 못했어요. "
        "Colab에서 만든 Chroma 저장소를 앱과 같은 위치에 넣어 주세요."
    )

if not has_api_key():
    st.info(
        "OpenAI API 키가 필요해요. "
        "Streamlit의 `.streamlit/secrets.toml`에 "
        '`OPENAI_API_KEY = "발급받은 키"`를 등록해 주세요.'
    )

# 기존 대화 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 추천 질문 버튼으로 들어온 질문 또는 직접 입력
user_input = st.chat_input("예: RAG와 임베딩의 차이를 설명해줘")
pending_question = st.session_state.pop("pending_question", None)
question = user_input or pending_question

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if not has_api_key():
            answer = "OpenAI API 키를 등록한 뒤 다시 질문해 주세요."
            st.warning(answer)
        elif not Path(CHROMA_DIR).exists():
            answer = (
                "문서 저장소 폴더를 찾지 못했어요. "
                "Chroma 저장소를 준비한 뒤 다시 실행해 주세요."
            )
            st.warning(answer)
        else:
            try:
                response_stream = get_chain().stream({"input": question})
                answer = st.write_stream(response_stream)
            except Exception as e:
                answer = f"답변을 생성하지 못했어요: {e}"
                st.error(answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

st.markdown(
    '<div class="footer-note">AIVLE School 학습 도우미 · 문서에 근거해 차근차근 답변합니다</div>',
    unsafe_allow_html=True,
)


