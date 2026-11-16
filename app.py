
import os
import streamlit as st
from operator import itemgetter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# Streamlit page configuration must come before other Streamlit UI calls.
st.set_page_config(
    page_title="AIVLE Whitepaper",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+KR:wght@400;500;600;700&display=swap');
:root { --ink:#1d1d1f; --muted:#6e6e73; --blue:#0071e3; --line:#e8e8ed; --panel:#f5f5f7; }
html, body, [class*="css"] { font-family: Inter, 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif; color:var(--ink); }
.stApp { background:#fbfbfd; }
[data-testid="stHeader"] { background:rgba(251,251,253,.86); }
[data-testid="stSidebar"] { background:#f5f5f7; border-right:1px solid var(--line); }
[data-testid="stSidebar"] h1 { font-size:1.25rem; letter-spacing:-.04em; }
.hero { padding:2.6rem 0 1.5rem; }
.eyebrow { color:var(--blue); font-size:.82rem; font-weight:600; letter-spacing:.04em; }
.hero-title { font-size:clamp(2.2rem,5vw,3.7rem); font-weight:700; letter-spacing:-.065em; line-height:1.08; margin:.6rem 0; }
.hero-copy { color:var(--muted); font-size:1.08rem; line-height:1.7; }
.soft-card { background:white; border:1px solid var(--line); border-radius:20px; padding:1.25rem 1.35rem; height:100%; box-shadow:0 3px 14px rgba(0,0,0,.025); }
.soft-card h3 { font-size:1.05rem; letter-spacing:-.025em; margin:0 0 .45rem; }
.soft-card p { color:var(--muted); line-height:1.6; margin:0; }
.section-note { color:var(--muted); margin-top:-.5rem; }
div[data-testid="stChatMessage"] { border:1px solid var(--line); border-radius:18px; padding:.85rem 1rem; background:white; }
div[data-testid="stChatInput"] { border-radius:18px; }
button[kind="primary"] { border-radius:999px; }
hr { border-color:var(--line); }
</style>
""", unsafe_allow_html=True)

FAQ = [
    ("하루 교육 타임테이블은 어떻게 되나요?", "기수별 시간표와 공지를 확인해 주세요. 체크인·교육·체크아웃 시간은 운영 상황에 따라 달라질 수 있습니다."),
    ("강의 다시보기를 할 수 있나요?", "다시보기 제공 여부와 기간은 강의별 안내와 AIVLE-EDU 공지를 확인해 주세요."),
    ("출석 인정 요청은 어떻게 하나요?", "마이페이지의 출결 현황에서 해당 날짜를 선택해 사유와 증빙서류를 제출합니다. 신청 기한과 인정 기준은 최신 공지를 확인해 주세요."),
    ("학교 수업이나 근로 일정은 어디에 등록하나요?", "마이페이지의 학사/근로 일정 메뉴에서 등록하는 것으로 안내되어 있습니다. 메뉴와 절차는 현재 기수 공지를 확인해 주세요."),
    ("프로젝트를 면접에서 어떻게 설명해야 하나요?", "문제와 목표, 본인 역할, 기술 선택 이유와 대안, 어려움과 해결 과정, 결과와 한계를 순서대로 설명해 보세요. 수치 성과는 측정 조건도 함께 말하면 좋습니다."),
    ("학습 계획은 어떻게 세우면 좋을까요?", "주간 목표를 작게 정하고 강의 복습, 코딩 연습, 프로젝트 시간을 나눈 뒤 매주 달성 여부를 돌아보며 조정해 보세요."),
]

# 제공된 실제 인터뷰와 공식 인터뷰 요약을 분리해 표기합니다.
ALUMNI = [
    {
        "name": "박건 선배", "cohort": "9기", "track": "DX 컨설턴트", "source": "사용자 제공 인터뷰",
        "tags": ["학습법", "프로젝트", "코딩테스트", "스터디"],
        "summary": "배운 내용을 프로젝트에 적용하고 코드 리뷰와 스터디로 학습을 확장한 경험",
        "answers": {
            "지원동기": "정보통신공학을 전공하고 인공지능을 연계전공했습니다. KT 디지털인재장학생 활동으로 종로구청과 ‘집회·교통정보 알림톡’을 기획해 상용화하며 디지털 서비스의 가치를 경험했고, KT에서 이런 서비스를 만들고 싶어 에이블스쿨에 도전했습니다.",
            "성장 비결": "수업 내용을 프로젝트에 적용했습니다. 미니프로젝트에서 조장을 맡아 분석 방향을 제시했고, 이후 프로젝트에서는 코드 리뷰와 모델링 보완을 담당했습니다. 빅프로젝트에서는 팀 대표 발표를 맡았습니다.",
            "코딩테스트 학습법": "다양한 문제를 풀고 한 문제에도 여러 풀이를 시도했습니다. 코딩마스터즈에서 다른 에이블러의 풀이와 비교하고 어려운 문제는 다시 풀며 복습했습니다. 코드 리뷰에서 우수리뷰로 선정되기도 했습니다.",
            "주도적으로 참여한 활동": "AICE 취득을 목표로 스터디를 만들고 운영했습니다. 프로젝트와 코딩테스트가 겹치는 시기에도 저녁마다 기출문제를 풀고 풀이를 공유해 서로의 부족한 개념을 보완했습니다.",
            "후배에게 전하는 말": "다른 사람과 비교하기보다 하루하루 최선을 다해 완주한 자신을 믿어 주세요. ‘나도 해냈다’는 경험이 다음 도전을 이어갈 힘이 되길 바랍니다.",
        },
    },
    {
        "name": "김태영 선배", "cohort": "9기", "track": "DX 컨설턴트", "source": "KT 공식 인터뷰 요약",
        "tags": ["프로젝트", "협업", "문제해결"],
        "summary": "프로젝트에서 문제와 근거를 확인하고 팀이 방향을 조정한 경험",
        "answers": {
            "프로젝트 경험": "공식 인터뷰 요약에 따르면 HeatConnect와 ForAble 프로젝트를 수행하며 자료 조사와 인터뷰로 아이디어를 구체화하고, 사용자 피드백을 반영해 서비스 범위를 정리했습니다.",
            "배운 점": "문제의 필요성과 데이터 근거를 확인하고, 사용자 검증과 팀 협업을 통해 결과물을 다듬는 과정이 중요하다는 점을 보여줍니다.",
        },
    },
]


def get_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        key = os.getenv("OPENAI_API_KEY", "")
    if key:
        os.environ["OPENAI_API_KEY"] = key
    return key


def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)


@st.cache_resource(show_spinner=False)
def get_chain(api_key):
    embedding = OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
    vectorstore = Chroma(
        collection_name="hr_rules",
        embedding_function=embedding,
        persist_directory="chroma_db",
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    system_message = """당신은 에이블스쿨 백서 안내 도우미입니다.
1. 반드시 제공된 문서 내용(context)에 근거해 한국어로 답하세요.
2. 문서에 없는 내용은 추측하지 말고 '업로드된 백서에서 확인되지 않습니다.'라고 답하세요.
3. 출석·일정 등 변경될 수 있는 내용은 현재 기수의 공식 공지를 확인하도록 안내하세요.
4. 답변은 친절하고 간결하게 작성하세요.

[문서]
{context}"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "{input}"),
    ])
    llm = ChatOpenAI(model="gpt-4o-mini", streaming=True, temperature=0, api_key=api_key)
    chain = (
        {"context": itemgetter("input") | retriever | format_docs, "input": itemgetter("input")}
        | prompt | llm | StrOutputParser()
    )
    return chain


st.sidebar.markdown("## ✳️ AIVLE 백서")
st.sidebar.caption("처음 시작하는 에이블러를 위한 안내")
page = st.sidebar.radio(
    "둘러보기",
    ["홈", "시작 안내", "FAQ", "학습 가이드", "선배 후기", "백서 챗봇"],
    label_visibility="collapsed",
)
st.sidebar.divider()
st.sidebar.caption("백서 기반 안내 · 기수별 공지 우선 확인")

if page == "홈":
    st.markdown('<div class="hero"><div class="eyebrow">AIVLE SCHOOL · COHORT GUIDE</div><div class="hero-title">배움의 첫걸음,<br>여기서 시작하세요.</div><div class="hero-copy">교육을 시작할 때 궁금한 정보와 선배들의 경험을 한곳에 담았습니다.</div></div>', unsafe_allow_html=True)
    cols = st.columns(3)
    cards = [("시작 안내", "교육 일정과 출결 절차를 확인하세요."), ("선배 후기", "기수와 주제별로 경험을 살펴보세요."), ("백서 챗봇", "백서 내용에 궁금한 점을 직접 물어보세요.")]
    for col, (title, desc) in zip(cols, cards):
        with col:
            st.markdown(f'<div class="soft-card"><h3>{title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
    st.write("")
    st.info("왼쪽 메뉴에서 원하는 내용을 선택해 보세요.")

elif page == "시작 안내":
    st.markdown('<div class="hero"><div class="eyebrow">GETTING STARTED</div><div class="hero-title">시작 전에 확인할 것</div><div class="hero-copy">일정과 운영 기준은 기수별 공지를 가장 먼저 확인해 주세요.</div></div>', unsafe_allow_html=True)
    for title, body in [
        ("교육 일정", "강의실 공지와 AIVLE-EDU의 강의 일정을 확인합니다."),
        ("출석과 인정 요청", "마이페이지 출결 현황에서 절차를 확인하고, 안내된 기한 내 증빙과 함께 제출합니다."),
        ("학사·근로 일정", "해당하는 경우 마이페이지의 학사/근로 일정 메뉴에 등록합니다."),
        ("학습 환경", "필요한 프로그램과 계정 로그인을 미리 확인하고 질문과 오류 해결 과정을 기록합니다."),
    ]:
        with st.expander(title):
            st.write(body)

elif page == "FAQ":
    st.markdown('<div class="hero"><div class="eyebrow">QUICK ANSWERS</div><div class="hero-title">자주 묻는 질문</div></div>', unsafe_allow_html=True)
    query = st.text_input("질문 검색", placeholder="출석, 강의, 프로젝트 등")
    matches = [(q, a) for q, a in FAQ if query.lower() in (q + a).lower()]
    if not matches:
        st.info("검색 결과가 없습니다.")
    for question, answer in matches:
        with st.expander(question):
            st.write(answer)

elif page == "학습 가이드":
    st.markdown('<div class="hero"><div class="eyebrow">LEARNING</div><div class="hero-title">나에게 맞는 학습 리듬</div><div class="hero-copy">작은 계획을 세우고, 꾸준히 돌아보며 조정해 보세요.</div></div>', unsafe_allow_html=True)
    for title, text in [
        ("수업 당일 복습", "핵심 개념과 헷갈린 부분을 짧게 정리합니다."),
        ("직접 구현", "예제를 따라 한 뒤 조건을 바꾸어 다시 작성합니다."),
        ("막힌 지점 기록", "오류와 해결 과정을 남겨 다음에 참고합니다."),
        ("프로젝트에 적용", "배운 기술을 작은 기능이라도 직접 사용합니다."),
        ("주간 회고", "잘된 점과 다음 주에 바꿀 점을 한 가지씩 적습니다."),
    ]:
        with st.expander(title):
            st.write(text)
    st.subheader("이번 주 나의 계획")
    st.text_input("이번 주 목표", placeholder="예: 파이썬 문제 5개 풀기")
    st.text_area("요일별 계획", placeholder="월: 강의 복습\n화: 코딩 연습\n수: 프로젝트")
    st.text_area("이번 주 회고", placeholder="잘한 점과 다음 주 보완할 점")

elif page == "선배 후기":
    st.markdown('<div class="hero"><div class="eyebrow">FROM AIVLERS</div><div class="hero-title">선배들의 경험</div><div class="hero-copy">기수와 주제로 찾아보고, 각자의 경험에서 나에게 맞는 힌트를 얻어 보세요.</div></div>', unsafe_allow_html=True)
    tags = sorted({tag for person in ALUMNI for tag in person["tags"]})
    selected_tag = st.selectbox("주제", ["전체 주제"] + tags)
    search = st.text_input("인터뷰 검색", placeholder="선배 이름이나 키워드")
    people = [p for p in ALUMNI if (selected_tag == "전체 주제" or selected_tag in p["tags"]) and search.lower() in (p["name"] + p["summary"] + " ".join(p["answers"].values())).lower()]
    for person in people:
        with st.container(border=True):
            st.markdown(f"### {person['name']}  ·  {person['cohort']} {person['track']} 트랙")
            st.caption(f"{person['source']}  ·  " + " / ".join(person["tags"]))
            st.write(person["summary"])
            for question, answer in person["answers"].items():
                with st.expander(question):
                    st.write(answer)
    if not people:
        st.info("조건에 맞는 인터뷰가 없습니다. 선배 인터뷰를 더 추가하면 이곳에서 함께 찾아볼 수 있어요.")

elif page == "백서 챗봇":
    st.markdown('<div class="hero"><div class="eyebrow">ASK THE WHITEPAPER</div><div class="hero-title">백서에 물어보세요.</div><div class="hero-copy">백서 내용을 검색해 근거에 맞춰 답변합니다. 문서에서 확인할 수 없는 내용은 모른다고 안내합니다.</div></div>', unsafe_allow_html=True)
    with st.expander("챗봇 연결 안내"):
        st.write("Chroma 컬렉션 `hr_rules`와 `chroma_db` 폴더에 백서 임베딩이 준비되어 있어야 합니다. Streamlit Secrets에 OpenAI API 키를 등록하세요.")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("대화 지우기"):
            st.session_state.messages = []
            st.rerun()
    for message in st.session_state.messages:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(message.content)
    api_key = get_api_key()
    if not api_key:
        st.warning("챗봇을 사용하려면 Streamlit Secrets에 `OPENAI_API_KEY`를 설정하세요.")
    user_input = st.chat_input("백서에 대해 궁금한 점을 입력하세요")
    if user_input:
        st.session_state.messages.append(HumanMessage(content=user_input))
        with st.chat_message("user"):
            st.markdown(user_input)
        if not api_key:
            st.session_state.messages.pop()
        else:
            try:
                chain = get_chain(api_key)
                with st.chat_message("assistant"):
                    with st.spinner("백서에서 관련 내용을 찾고 있어요…"):
                        answer = st.write_stream(chain.stream({"input": user_input}))
                st.session_state.messages.append(AIMessage(content=answer or ""))
            except Exception as error:
                st.error("챗봇에 연결하지 못했습니다. API 키와 ChromaDB 경로를 확인해 주세요.")
                st.caption(str(error))
