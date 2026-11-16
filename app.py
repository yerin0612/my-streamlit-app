import smtplib
import streamlit as st
from datetime import date
from email.message import EmailMessage
from email.policy import SMTP
from openai import OpenAI

st.set_page_config(
    page_title="에이블스쿨 백서",
    page_icon="📘",
    layout="wide"
)

# 임시 콘텐츠: 백서 내용에 맞게 수정하세요.
FAQ = [
    {
        "질문": "하루 교육 타임테이블은 어떻게 되나요?",
        "답변": "기수별 공지를 확인하세요. 교육 시간과 체크인·체크아웃 시간은 운영 상황에 따라 달라질 수 있습니다."
    },
    {
        "질문": "강의 다시보기를 할 수 있나요?",
        "답변": "다시보기 제공 여부와 기간은 강의별 안내 및 AIVLE-EDU 공지를 확인하세요."
    },
    {
        "질문": "출석 인정 요청은 어떻게 하나요?",
        "답변": "마이페이지의 출결 현황에서 해당 날짜를 선택해 사유와 증빙서류를 제출하세요. 최신 절차는 공식 안내를 확인해야 합니다."
    },
    {
        "질문": "프로젝트는 면접에서 어떻게 설명해야 하나요?",
        "답변": "문제와 목표, 본인의 역할, 기술 선택 이유, 해결 과정, 결과와 한계를 순서대로 설명하세요. 성과를 수치로 말할 때는 측정 조건도 함께 제시하면 좋습니다."
    },
    {
        "질문": "학습 계획은 어떻게 세우면 좋을까요?",
        "답변": "주간 목표를 작게 정하고, 강의 복습·코딩 연습·프로젝트 작업 시간을 나눠 계획해 보세요. 매주 달성 여부를 점검하며 조정하면 좋습니다."
    },
]

INTERVIEW = [
    ("자기소개와 지원동기",
     "정보통신공학을 전공하고 인공지능을 연계전공했습니다. KT 디지털인재장학생 활동으로 종로구청과 ‘집회·교통정보 알림톡’을 기획해 상용화하며 디지털 서비스의 가치를 경험했습니다. KT에서 이런 서비스를 만들고 싶어 에이블스쿨에 도전했습니다."),
    ("우수 수료생이 된 비결",
     "배운 내용을 프로젝트에 적용하려고 노력했습니다. 미니프로젝트에서 조장을 맡았고, 이후 프로젝트에서는 코드 리뷰와 모델링 보완을 담당했습니다. 빅프로젝트에서는 팀 대표 발표를 맡았습니다."),
    ("코딩테스트 학습법",
     "다양한 문제를 풀고 여러 풀이를 비교했습니다. 코딩마스터즈 코드 리뷰에 참여하고 어려웠던 문제를 다시 풀며 부족한 부분을 보완했습니다."),
    ("주도적으로 참여한 활동",
     "AICE 취득을 목표로 소규모 스터디를 만들고 운영했습니다. 매일 기출문제를 풀고 풀이를 공유하며 함께 공부하는 분위기를 만들었습니다."),
    ("후배에게 전하는 말",
     "다른 사람과 비교하기보다 하루하루 최선을 다해 완주한 자신을 믿어 주세요. ‘나도 해냈다’는 경험이 다음 도전을 이어갈 힘이 되길 바랍니다."),
]

# 사이드바 메뉴
st.sidebar.title("📘 에이블스쿨 백서")
page = st.sidebar.radio(
    "메뉴",
    ["홈", "시작 안내", "FAQ", "학습 가이드", "선배 후기"]
)

if page == "홈":
    st.title("에이블스쿨 백서")
    st.subheader("처음 시작하는 에이블러를 위한 안내")
    st.write("교육 시작 전 궁금한 점부터 학습 전략과 선배들의 경험까지 확인해 보세요.")

    col1, col2, col3 = st.columns(3)
    col1.metric("FAQ", f"{len(FAQ)}개")
    col2.metric("선배 인터뷰", f"{len(INTERVIEW)}개 질문")
    col3.metric("학습 가이드", "주간 계획")

    st.info("원하는 메뉴를 왼쪽에서 선택해 주세요.")

elif page == "시작 안내":
    st.title("시작 안내")
    st.write("교육 일정, 플랫폼 사용법, 출결 절차를 확인하는 페이지입니다.")

    with st.expander("교육 시작 전 체크리스트", expanded=True):
        st.checkbox("AIVLE-EDU 로그인 확인")
        st.checkbox("기수 공지와 강의 일정 확인")
        st.checkbox("학습 환경 및 필요한 프로그램 준비")
        st.checkbox("개인 주간 학습 시간 확보")

    st.warning("교육 시간과 출결 인정 기준은 기수별 공식 공지를 우선 확인하세요.")

elif page == "FAQ":
    st.title("자주 묻는 질문")
    search = st.text_input("질문 검색", placeholder="예: 출석, 강의, 프로젝트")

    results = [
        item for item in FAQ
        if search.strip() in item["질문"] or search.strip() in item["답변"]
    ]

    if not results:
        st.info("검색 결과가 없습니다.")
    else:
        for item in results:
            with st.expander(item["질문"]):
                st.write(item["답변"])

elif page == "학습 가이드":
    st.title("성공적인 학습 전략")
    st.write("계획은 작게 세우고, 매주 돌아보며 조정해 보세요.")

    st.markdown("""
    1. **수업 당일 복습하기**: 핵심 개념과 헷갈린 부분을 짧게 정리합니다.
    2. **직접 코드 작성하기**: 예제를 그대로 따라 친 뒤, 조건을 바꿔 다시 구현합니다.
    3. **막힌 지점 기록하기**: 오류와 해결 과정을 남겨 다음에 참고합니다.
    4. **프로젝트에서 적용하기**: 배운 기술을 작은 기능이라도 직접 사용해 봅니다.
    5. **주간 회고하기**: 잘된 점과 다음 주에 바꿀 점을 한 가지씩 적습니다.
    """)

    st.subheader("이번 주 나의 학습 계획")
    st.text_input("이번 주 목표", placeholder="예: 파이썬 문제 5개 풀기")
    st.text_area("요일별 계획", placeholder="월: 강의 복습\n화: 코딩 연습\n수: 프로젝트")
    st.text_area("이번 주 회고", placeholder="잘한 점과 다음 주 보완할 점")

elif page == "선배 후기":
    st.title("선배 후기")
    st.caption("9기 DX 컨설턴트 트랙 우수 수료생 박건 선배 인터뷰")

    for question, answer in INTERVIEW:
        with st.expander(question):
            st.write(answer)

    st.divider()
    st.subheader("프로젝트 면접 답변 정리")
    st.write(
        "문제와 목표 → 본인 역할 → 기술 선택 이유와 대안 → "
        "장애물과 해결 과정 → 결과와 한계 순서로 정리해 보세요. "
        "성과를 수치로 제시할 때는 측정 조건도 함께 설명하세요."
    )
