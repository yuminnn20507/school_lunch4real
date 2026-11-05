
import re
from itertools import combinations

import pandas as pd
import streamlit as st
import plotly.express as px


# ==========================================
# 1. 페이지 설정
# ==========================================

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")
st.markdown(
    "송탄고 급식 데이터를 이용해 함께 등장하는 메뉴와 "
    "메뉴 사이의 연관 규칙을 찾아봅니다."
)

DATA_URL = (
    "https://raw.githubusercontent.com/"
    "it-teacher-go/data-share-/main/"
    "songtan_meals_184.csv"
)


# ==========================================
# 2. 데이터 불러오기
# ==========================================

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"필수 열이 없습니다: {col}")

    df = df.dropna(subset=["메뉴"]).copy()

    return df


# ==========================================
# 3. 메뉴 이름 정리
# ==========================================

def clean_menu(menu):
    """
    메뉴 이름에서 괄호와 괄호 안의 내용을 제거한다.
    괄호가 중첩된 경우에도 반복해서 제거한다.
    """

    menu = str(menu).strip()

    while True:
        cleaned = re.sub(r"\([^()]*\)", "", menu)

        if cleaned == menu:
            break

        menu = cleaned

    # 불필요한 공백 정리
    menu = re.sub(r"\s+", " ", menu).strip()

    return menu


# ==========================================
# 4. 장바구니 데이터 만들기
# ==========================================

@st.cache_data
def make_transactions(df):
    transactions = []

    for menu_text in df["메뉴"]:

        # 세로줄 기준으로 메뉴 분리
        menus = str(menu_text).split("|")

        # 괄호 제거
        menus = [clean_menu(menu) for menu in menus]

        # 빈 메뉴 제거 및 같은 날 중복 메뉴 제거
        menus = sorted(set(menu for menu in menus if menu))

        transactions.append(menus)

    return transactions


# ==========================================
# 5. 연관 규칙 분석
# ==========================================

@st.cache_data
def make_rules(transactions):

    total_days = len(transactions)

    # 메뉴별 등장 횟수
    menu_count = {}

    # 메뉴 쌍별 동시 등장 횟수
    pair_count = {}

    for basket in transactions:

        for menu in basket:
            menu_count[menu] = menu_count.get(menu, 0) + 1

        # 같은 날 나온 메뉴의 모든 조합
        for pair in combinations(sorted(basket), 2):
            pair_count[pair] = pair_count.get(pair, 0) + 1

    # 연관 규칙 생성
    rules = []

    for (menu_a, menu_b), count in pair_count.items():

        support = count / total_days

        confidence_ab = count / menu_count[menu_a]
        confidence_ba = count / menu_count[menu_b]

        support_a = menu_count[menu_a] / total_days
        support_b = menu_count[menu_b] / total_days

        lift_ab = confidence_ab / support_b
        lift_ba = confidence_ba / support_a

        # A → B
        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return rules_df, menu_count, pair_count


# ==========================================
# 6. 데이터 분석 실행
# ==========================================

try:
    df = load_data()

    transactions = make_transactions(df)

    rules_df, menu_count, pair_count = make_rules(transactions)

except Exception as e:
    st.error(f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}")
    st.stop()


total_days = len(transactions)
total_menus = len(menu_count)
total_pairs = len(pair_count)


# ==========================================
# 7. 요약 정보
# ==========================================

st.subheader("📊 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days:,}일")
col2.metric("메뉴 종류 수", f"{total_menus:,}종")
col3.metric("함께 나온 메뉴 쌍", f"{total_pairs:,}쌍")

st.divider()


# ==========================================
# 8. 메뉴 선택 및 정렬
# ==========================================

st.subheader("🔍 연관 규칙 탐색")

col1, col2 = st.columns([2, 1])

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택",
        options=["전체 메뉴"] + sorted(menu_count.keys())
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"]
    )


# 메뉴 필터링
filtered_rules = rules_df.copy()

if selected_menu != "전체 메뉴":
    filtered_rules = filtered_rules[
        (filtered_rules["조건"] == selected_menu) |
        (filtered_rules["결과"] == selected_menu)
    ].copy()


# 정렬
sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_rules = filtered_rules.sort_values(
    by=[sort_column, "신뢰도", "동시"],
    ascending=[False, False, False]
).reset_index(drop=True)


# ==========================================
# 9. 연관 규칙 표
# ==========================================

st.subheader("📋 메뉴 연관 규칙")

st.caption(
    "조건 메뉴가 나왔을 때 결과 메뉴가 함께 나오는 관계입니다. "
    "반대 방향의 규칙도 별도로 표시합니다."
)

if filtered_rules.empty:

    st.warning("선택한 메뉴에 해당하는 연관 규칙이 없습니다.")

else:

    display_df = filtered_rules.copy()

    # 지지도와 신뢰도는 백분율로 표시
    display_df["지지도"] = (
        display_df["지지도"] * 100
    ).map(lambda x: f"{x:.2f}%")

    display_df["신뢰도"] = (
        display_df["신뢰도"] * 100
    ).map(lambda x: f"{x:.2f}%")

    display_df["향상도"] = (
        display_df["향상도"]
    ).map(lambda x: f"{x:.3f}")

    display_df["동시"] = display_df["동시"].astype(int)

    st.dataframe(
        display_df[
            ["조건", "결과", "동시", "지지도", "신뢰도", "향상도"]
        ],
        use_container_width=True,
        hide_index=True,
        height=500
    )

    st.caption(
        f"현재 표시 중인 규칙: {len(filtered_rules):,}개"
    )


# ==========================================
# 10. 향상도 상위 10개 그래프
# ==========================================

st.divider()

st.subheader("📈 향상도 TOP 10")

st.markdown(
    "향상도가 높은 순서로 메뉴 조합을 보여줍니다. "
    "메뉴를 선택하면 해당 메뉴가 포함된 규칙만 그래프에 표시됩니다."
)

if filtered_rules.empty:

    st.info("그래프로 표시할 규칙이 없습니다.")

else:

    top10 = (
        filtered_rules
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=[False, False, False]
        )
        .head(10)
        .copy()
    )

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    # 그래프 순서 정리
    top10 = top10.sort_values("향상도", ascending=True)

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        hover_data={
            "조건": True,
            "결과": True,
            "동시": True,
            "지지도": ":.2%",
            "신뢰도": ":.2%",
            "향상도": ":.3f",
            "규칙": False
        },
        labels={
            "향상도": "향상도 (Lift)",
            "규칙": "메뉴 연관 규칙"
        },
        title="향상도 상위 10개 메뉴 연관 규칙"
    )

    fig.update_traces(
        texttemplate="%{text:.3f}",
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        height=550,
        xaxis_title="향상도",
        yaxis_title="",
        yaxis=dict(
            automargin=True
        ),
        margin=dict(
            l=20,
            r=70,
            t=70,
            b=40
        )
    )

    fig.add_vline(
        x=1,
        line_dash="dash",
        annotation_text="향상도 = 1",
        annotation_position="top"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==========================================
# 11. 지표 설명
# ==========================================

st.divider()

with st.expander("📖 연관 규칙 분석 지표 알아보기"):

    st.markdown("""
    **1. 지지도 (Support)**

    전체 급식 일수 중 두 메뉴가 함께 나온 날의 비율입니다.

    **2. 신뢰도 (Confidence)**

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 날의 비율입니다.

    **3. 향상도 (Lift)**

    두 메뉴가 서로 독립적으로 등장한다고 가정했을 때와 비교하여
    실제로 얼마나 자주 함께 등장했는지를 나타냅니다.

    - 향상도 > 1 : 양의 연관성
    - 향상도 = 1 : 서로 독립적인 관계
    - 향상도 < 1 : 음의 연관성

    **주의:** 향상도가 높다고 해서 반드시 두 메뉴 사이에
    인과관계가 있다는 뜻은 아닙니다.
    """)
