import hashlib
import os
import tempfile
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="에이블스쿨 백서", page_icon="📘", layout="wide")

FAQ = [
    ("하루 교육 타임테이블은 어떻게 되나요?", "기수별 시간표와 공지를 확인해 주세요. 체크인·교육·체크아웃 시간은 운영 상황에 따라 달라질 수 있습니다."),
    ("강의 다시보기를 할 수 있나요?", "다시보기 제공 여부와 기간은 강의별 안내와 AIVLE-EDU 공지를 확인해 주세요."),
    ("출석 인정 요청은 어떻게 하나요?", "마이페이지의 출결 현황에서 해당 날짜를 선택해 사유와 증빙서류를 제출합니다. 신청 기한과 인정 기준은 최신 공지를 확인해 주세요."),
    ("학교 수업이나 근로 일정은 어디에 등록하나요?", "마이페이지의 학사/근로 일정 메뉴에서 등록하는 것으로 안내되어 있습니다. 메뉴와 절차는 현재 기수 공지를 확인해 주세요."),
    ("프로젝트를 면접에서 어떻게 설명해야 하나요?", "문제와 목표, 본인 역할, 기술을 선택한 이유와 대안, 어려움과 해결 과정, 결과와 한계를 순서대로 설명해 보세요. 수치 성과는 측정 조건도 함께 말하면 좋습니다."),
    ("학습 계획은 어떻게 세우면 좋을까요?", "주간 목표를 작게 정하고 강의 복습, 코딩 연습, 프로젝트 시간을 나눈 뒤 매주 달성 여부를 돌아보며 조정해 보세요."),
]

# 인터뷰 원문/백서에 제공된 내용만 정리했습니다. 다른 선배 사례는 추가 인터뷰를 받아 늘려 주세요.
ALUMNI = [
    {
        "name": "박건 선배", "cohort": "9기", "track": "DX 컨설턴트", "tags": ["학습법", "프로젝트", "코딩테스트", "스터디"],
        "summary": "배운 내용을 프로젝트에 적용하고, 코드 리뷰와 스터디로 학습을 확장한 경험",
        "answers": {
            "지원동기": "정보통신공학 전공 및 인공지능 연계전공. KT 디지털인재장학생 활동으로 종로구청과 ‘집회·교통정보 알림톡’을 기획해 상용화했고, 디지털 서비스의 가치를 경험해 에이블스쿨에 도전했습니다.",
            "성장 비결": "수업 내용을 프로젝트에 적용했습니다. 미니프로젝트에서 조장을 맡아 분석 방향을 제시했고, 이후 프로젝트에서는 코드 리뷰와 모델링 보완을 담당했습니다. 빅프로젝트에서는 팀 대표 발표를 맡았습니다.",
            "코딩테스트": "다양한 문제를 풀고 한 문제에도 여러 풀이를 시도했습니다. 코딩마스터즈에서 다른 에이블러의 풀이와 비교하고, 어려운 문제는 다시 풀며 복습했습니다. 코드 리뷰에서 우수리뷰로 선정되기도 했습니다.",
            "주도적 활동": "AICE 취득을 목표로 스터디를 만들고 운영했습니다. 프로젝트와 코딩테스트가 겹치는 시기에도 저녁마다 기출문제를 풀고 풀이를 공유해 서로의 부족한 개념을 보완했습니다.",
            "후배에게": "다른 사람과 비교하기보다 하루하루 최선을 다해 완주한 자신을 믿어 주세요. ‘나도 해냈다’는 경험이 다음 도전을 이어갈 힘이 되길 바랍니다.",
        },
    },
    {
        "name": "김태영 선배", "cohort": "9기", "track": "DX 컨설턴트", "tags": ["프로젝트", "협업", "문제해결"],
        "summary": "공식 인터뷰에 소개된 프로젝트 경험: 문제와 근거를 확인하고 팀이 방향을 조정한 과정",
        "answers": {
            "프로젝트 경험": "공식 인터뷰 요약에 따르면 HeatConnect와 ForAble 프로젝트를 수행하며, 자료 조사와 인터뷰로 아이디어를 구체화하고 사용자 피드백을 반영해 서비스 범위를 정리했습니다.",
            "배운 점": "문제의 필요성과 데이터의 근거를 확인하고, 사용자 검증과 팀 협업을 통해 결과물을 다듬는 과정이 중요하다는 점을 보여줍니다.",
        },
    },
]


def get_api_key():
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return os.getenv("OPENAI_API_KEY", "")


@st.cache_resource(show_spinner="백서 내용을 읽고 질문 기능을 준비하고 있어요…")
def make_retriever(pdf_bytes: bytes, file_hash: str):
    # file_hash를 캐시 키로 사용합니다.
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
    from langchain_pymupdf4llm import PyMuPDF4LLMLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
        temp.write(pdf_bytes)
        temp_path = temp.name
    try:
        docs = PyMuPDF4LLMLoader(temp_path).load()
        chunks = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100).split_documents(docs)
        store = Chroma.from_documents(chunks, OpenAIEmbeddings(), collection_name=f"aivle_{file_hash[:12]}")
        return store.as_retriever(search_kwargs={"k": 4})
    finally:
        Path(temp_path).unlink(missing_ok=True)


def ask_whitepaper(question, retriever, api_key):
    from langchain_openai import ChatOpenAI
    docs = retriever.invoke(question)
    context = "\n\n".join(doc.page_content for doc in docs)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    prompt = f"""당신은 에이블스쿨 백서 안내 도우미입니다. 아래 백서 내용에 근거해 한국어로 친절하고 간결하게 답하세요.
백서에 답이 없거나 불확실하면 추측하지 말고 '백서에서 확인하기 어렵습니다. 현재 기수의 공식 공지를 확인해 주세요.'라고 말하세요.

[백서 내용]
{context}

[질문]
{question}
"""
    answer = llm.invoke(prompt).content
    pages = sorted({str(d.metadata.get("page", "")) for d in docs if d.metadata.get("page") is not None})
    return answer, pages


st.sidebar.title("📘 에이블스쿨 백서")
page = st.sidebar.radio("메뉴", ["홈", "시작 안내", "FAQ", "학습 가이드", "선배 후기", "백서에 질문하기"])

if page == "홈":
    st.title("에이블스쿨 백서")
    st.subheader("처음 시작하는 에이블러를 위한 안내")
    st.write("시작 안내부터 FAQ, 학습 계획, 선배들의 경험까지 한곳에서 살펴보세요.")
    cols = st.columns(4)
    for col, number, label in zip(cols, ["01", "02", "03", "04"], ["시작 안내", "FAQ", "학습 가이드", "선배 후기"]):
        with col:
            st.metric(label, number)
    st.info("백서 내용을 직접 묻고 싶다면 왼쪽 메뉴의 ‘백서에 질문하기’를 선택하세요.")

elif page == "시작 안내":
    st.title("시작 안내")
    st.write("교육 일정과 플랫폼 안내는 기수에 따라 달라질 수 있으니 최신 공지를 함께 확인하세요.")
    for title, body in [
        ("교육 일정", "강의실 공지와 AIVLE-EDU의 강의 일정을 확인합니다."),
        ("출석과 인정 요청", "마이페이지 출결 현황에서 절차를 확인하고, 인정 요청은 안내된 기한 내에 증빙과 함께 제출합니다."),
        ("학사·근로 일정", "해당하는 경우 마이페이지의 학사/근로 일정 메뉴에 등록합니다."),
        ("학습 환경", "필요한 프로그램과 계정 로그인을 미리 확인하고, 질문과 오류 해결 과정을 기록합니다."),
    ]:
        with st.expander(title):
            st.write(body)

elif page == "FAQ":
    st.title("자주 묻는 질문")
    query = st.text_input("질문 검색", placeholder="예: 출석, 프로젝트, 강의")
    matches = [(q, a) for q, a in FAQ if query.lower() in (q + a).lower()]
    if not matches:
        st.info("검색 결과가 없습니다.")
    for q, a in matches:
        with st.expander(q):
            st.write(a)

elif page == "학습 가이드":
    st.title("성공적인 학습 전략")
    st.markdown("""
    - **수업 당일 복습:** 핵심 개념과 헷갈린 부분을 짧게 정리합니다.
    - **직접 구현:** 예제를 따라 한 뒤 조건을 바꾸어 다시 작성합니다.
    - **막힌 지점 기록:** 오류와 해결 과정을 남겨 다음에 참고합니다.
    - **프로젝트에 적용:** 배운 기술을 작은 기능이라도 직접 사용합니다.
    - **주간 회고:** 잘된 점과 다음 주에 바꿀 점을 한 가지씩 적습니다.
    """)
    st.subheader("이번 주 나의 학습 계획")
    st.text_input("이번 주 목표", placeholder="예: 파이썬 문제 5개 풀기", key="goal")
    st.text_area("요일별 계획", placeholder="월: 강의 복습\n화: 코딩 연습\n수: 프로젝트", key="plan")
    st.text_area("이번 주 회고", placeholder="잘한 점과 다음 주 보완할 점", key="review")

elif page == "선배 후기":
    st.title("선배 후기")
    st.write("기수와 주제별로 살펴보세요. 새 인터뷰를 받으면 ALUMNI 목록에 같은 형식으로 추가할 수 있습니다.")
    all_tags = sorted({tag for person in ALUMNI for tag in person["tags"]})
    selected_tag = st.selectbox("주제 필터", ["전체"] + all_tags)
    search = st.text_input("선배 또는 내용 검색", placeholder="예: 박건, 코딩테스트, 협업")
    people = [p for p in ALUMNI if (selected_tag == "전체" or selected_tag in p["tags"]) and search.lower() in (p["name"] + p["summary"] + " ".join(p["answers"].values())).lower()]
    if not people:
        st.info("조건에 맞는 인터뷰가 없습니다.")
    for person in people:
        with st.container(border=True):
            st.subheader(f"{person['name']} · {person['cohort']} {person['track']} 트랙")
            st.caption(" / ".join(person["tags"]))
            st.write(person["summary"])
            for question, answer in person["answers"].items():
                with st.expander(question):
                    st.write(answer)

elif page == "백서에 질문하기":
    st.title("백서에 질문하기")
    st.write("백서 파일을 선택하고 궁금한 점을 입력하면, 문서 내용을 찾아 답변합니다.")
    api_key = get_api_key()
    if not api_key:
        st.warning("OpenAI API 키를 설정해야 챗봇을 사용할 수 있습니다. Streamlit 배포 설정의 Secrets에 OPENAI_API_KEY를 등록하세요.")
        st.code('OPENAI_API_KEY = "발급받은_API_키"', language="toml")
    default_pdf = Path(__file__).parent / "AIVLE School 백서.pdf"
    uploaded = st.file_uploader("백서 PDF", type=["pdf"])
    if uploaded:
        pdf_bytes = uploaded.getvalue()
        pdf_label = uploaded.name
    elif default_pdf.exists():
        pdf_bytes = default_pdf.read_bytes()
        pdf_label = default_pdf.name
    else:
        pdf_bytes = None
        pdf_label = None
    if not pdf_bytes:
        st.info("백서 PDF를 업로드하거나 앱과 같은 GitHub 저장소에 `AIVLE School 백서.pdf`라는 이름으로 추가해 주세요.")
    elif api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        st.caption(f"질문 대상: {pdf_label}")
        try:
            retriever = make_retriever(pdf_bytes, hashlib.sha256(pdf_bytes).hexdigest())
            if "chat_history" not in st.session_state:
                st.session_state.chat_history = []
            for item in st.session_state.chat_history:
                with st.chat_message(item["role"]):
                    st.markdown(item["content"])
            question = st.chat_input("백서에 대해 궁금한 점을 입력하세요")
            if question:
                st.session_state.chat_history.append({"role": "user", "content": question})
                with st.chat_message("user"):
                    st.markdown(question)
                with st.chat_message("assistant"):
                    with st.spinner("백서에서 관련 내용을 찾는 중이에요…"):
                        answer, pages = ask_whitepaper(question, retriever, api_key)
                    st.markdown(answer)
                    if pages:
                        st.caption("참고한 PDF 페이지: " + ", ".join(pages))
                st.session_state.chat_history.append({"role": "assistant", "content": answer})
        except Exception as exc:
            st.error("질문 기능을 준비하지 못했습니다. PDF 파일과 API 키, requirements.txt를 확인해 주세요.")
            st.caption(f"오류 정보: {exc}")
