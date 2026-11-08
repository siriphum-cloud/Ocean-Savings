# -*- coding: utf-8 -*-
"""
Deep Ocean Savings 🐋
โปรแกรมคำนวณเงินฝากแบบดอกเบี้ยทบต้น + ฝากเพิ่ม "ต้นงวด"
งานวิชา AM200 บทที่ 3 : ความสัมพันธ์เวียนเกิด (Recurrence Relation)

วิธีรัน (พิมพ์ในหน้าต่างคำสั่ง):   python -m streamlit run app.py

โครงสร้างไฟล์นี้มี 4 ส่วน
  ส่วนที่ 1  ค่าที่ธนาคารกำหนด (ดอกเบี้ย)
  ส่วนที่ 2  คณิตศาสตร์ = สูตรที่หาด้วยมือใน PDF   <-- หัวใจของงาน
  ส่วนที่ 3  เครื่องมือช่วยแสดงผล (ตัวเลข กราฟ ตาราง)
  ส่วนที่ 4  หน้าจอโปรแกรม (ปุ่ม ช่องกรอก ผลลัพธ์)
"""

import math
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st


# ============================================================
# ส่วนที่ 1 : ค่าที่ธนาคารกำหนด
# ============================================================
ANNUAL_RATE = 0.02  # ดอกเบี้ย 2% ต่อปี แบบทบต้น (แก้ตรงนี้ที่เดียว ทั้งโปรแกรมเปลี่ยนตาม)

FREQ_YEAR = "ทุกปี"
FREQ_MONTH = "ทุกเดือน"


# ============================================================
# ส่วนที่ 2 : คณิตศาสตร์ (สูตรที่หาด้วยมือใน PDF)
#   P = เงินต้น, r = ดอกเบี้ยต่องวด, d = เงินฝากเพิ่มต้นงวด
#   n = จำนวนงวด, B_n = เงินในบัญชีเมื่อสิ้นงวดที่ n
# ============================================================
def rate_and_periods(years, freq):
    """แปลงหน่วยให้ตรงกันก่อนใช้สูตร  ->  คืนค่า (r, n)
    ฝากทุกปี   : r = ดอกเบี้ยต่อปี,        n = จำนวนปี
    ฝากทุกเดือน : r = ดอกเบี้ยต่อปี / 12,   n = 12 x จำนวนปี
    """
    if freq == FREQ_MONTH:
        return ANNUAL_RATE / 12, years * 12
    return ANNUAL_RATE, years


def balance(P, r, d, n):
    """สูตรหลัก (สูตรทั่วไปที่ใส่ n ได้ทันที)
        B_n = (P + (1+r)d/r)(1+r)^n - (1+r)d/r
    """
    if r == 0:  # ไม่มีดอกเบี้ย -> หารด้วย 0 ไม่ได้ จึงใช้ B_n = P + n*d
        return P + n * d
    A = (1 + r) * d / r
    return (P + A) * (1 + r) ** n - A


def balance_by_recurrence(P, r, d, n):
    """ใช้ "ตรวจคำตอบ" เท่านั้น: วนสมการเวียนเกิดทีละงวด
        B_k = (1+r)(B_{k-1} + d),   B_0 = P
    """
    B = P
    for _ in range(n):
        B = (1 + r) * (B + d)
    return B


def deposit_factor(r, n):
    """ตัวคูณของ d ในสูตร: (1+r)((1+r)^n - 1)/r   (ถ้า r = 0 จะเท่ากับ n)"""
    if r == 0:
        return n
    return (1 + r) * ((1 + r) ** n - 1) / r


# --- สูตรสำหรับ "ตั้งเป้าหมาย" : ให้ B_n = G (เป้าหมาย) แล้วย้ายข้างสูตรหลัก ---
def need_d(G, P, r, n):
    """รู้เงินต้น P  ->  ต้องฝากเพิ่มงวดละ d เท่าไหร่"""
    return (G - P * (1 + r) ** n) / deposit_factor(r, n)


def need_P(G, d, r, n):
    """รู้เงินฝากเพิ่ม d  ->  ต้องมีเงินต้น P เท่าไหร่"""
    return (G - d * deposit_factor(r, n)) / (1 + r) ** n


def need_equal(G, r, n):
    """ให้เงินต้นเท่ากับเงินฝากเพิ่ม (P = d)  ->  ค่านั้นเท่าไหร่"""
    return G / ((1 + r) ** n + deposit_factor(r, n))


# ============================================================
# ส่วนที่ 3 : เครื่องมือช่วยแสดงผล
# ============================================================
def money(x):
    """10000.5 -> '10,000.50'"""
    return f"{x:,.2f}"


def tex(x, dp=2):
    """ตัวเลขสำหรับเขียนในสูตร LaTeX (ใส่ลูกน้ำแบบที่ LaTeX อ่านได้)"""
    return f"{x:,.{dp}f}".replace(",", "{,}")


def short(x):
    """ตัวเลขทศนิยมไม่เกิน 6 ตำแหน่ง ตัดศูนย์ท้าย: 1.020000 -> 1.02"""
    return f"{x:.6f}".rstrip("0").rstrip(".")


def round_up(x):
    """ปัดขึ้นเป็นสตางค์ เพื่อให้ถึงเป้าแน่นอน"""
    return math.ceil(x * 100 - 1e-9) / 100


def card(label, value, sub="", kind=""):
    return (f'<div class="ocean-card {kind}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div><div class="sub">{sub}</div></div>')


def show_cards(*cards):
    st.markdown('<div class="card-row">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def note(text, kind=""):
    st.markdown(f'<div class="note {kind}">{text}</div>', unsafe_allow_html=True)


def growth_table(P, r, d, n):
    """ยอดเงินทุกงวด k = 0, 1, ..., n (คำนวณจากสูตรหลัก)"""
    rows = [{"งวดที่": k,
             "ยอดเงินในบัญชี": balance(P, r, d, k),
             "เงินที่ฝากเข้าไปรวม": P + k * d} for k in range(n + 1)]
    return pd.DataFrame(rows)


def growth_chart(df, unit, goal=None):
    """กราฟเงินโตขึ้นทุกงวด (ธีมมหาสมุทร)"""
    series = ["ยอดเงินในบัญชี", "เงินที่ฝากเข้าไปรวม"]
    long = df.melt("งวดที่", value_vars=series, var_name="รายการ", value_name="บาท")
    x = alt.X("งวดที่:Q", title=f"งวดที่ ({unit})", axis=alt.Axis(format="d", tickMinStep=1))

    water = alt.Chart(df).mark_area(
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                           stops=[alt.GradientStop(color="rgba(46,230,214,0.02)", offset=0),
                                  alt.GradientStop(color="rgba(46,230,214,0.45)", offset=1)])
    ).encode(x=x, y="ยอดเงินในบัญชี:Q")

    lines = alt.Chart(long).mark_line(strokeWidth=2.6).encode(
        x=x,
        y=alt.Y("บาท:Q", title="บาท", axis=alt.Axis(format=",.0f")),
        color=alt.Color("รายการ:N", scale=alt.Scale(domain=series, range=["#2EE6D6", "#FFB86B"]),
                        legend=alt.Legend(title=None, orient="top")),
        strokeDash=alt.StrokeDash("รายการ:N", scale=alt.Scale(domain=series, range=[[1, 0], [6, 4]]),
                                  legend=None),
        tooltip=[alt.Tooltip("งวดที่:Q"), alt.Tooltip("รายการ:N"), alt.Tooltip("บาท:Q", format=",.2f")],
    )

    layers = [water, lines]
    if goal is not None:
        g = pd.DataFrame({"เป้าหมาย": [goal], "ข้อความ": [f"🎯 เป้าหมาย {goal:,.0f}"]})
        layers.append(alt.Chart(g).mark_rule(color="#FF8FB1", strokeDash=[4, 4], strokeWidth=2)
                      .encode(y="เป้าหมาย:Q"))
        layers.append(alt.Chart(g).mark_text(color="#FF8FB1", align="left", dx=6, dy=-8, fontSize=13)
                      .encode(y="เป้าหมาย:Q", x=alt.value(0), text="ข้อความ:N"))

    chart = (alt.layer(*layers).properties(height=340)
             .configure(background="transparent")
             .configure_view(strokeWidth=0)
             .configure_axis(labelColor="#a9d8ec", titleColor="#a9d8ec",
                             gridColor="rgba(255,255,255,0.08)", domainColor="#2a6d93")
             .configure_legend(labelColor="#e3f6ff", labelFontSize=13))
    st.altair_chart(chart, theme=None, width="stretch")


def show_table(P, r, d, n, freq):
    """ตารางยอดเงินรายงวด: ต้นงวด -> ฝากเพิ่ม -> ได้ดอกเบี้ย -> สิ้นงวด"""
    rows = []
    for k in range(1, n + 1):
        start, end = balance(P, r, d, k - 1), balance(P, r, d, k)
        row = {"งวดที่": k}
        if freq == FREQ_MONTH:
            row["ปีที่"] = math.ceil(k / 12)
        row.update({"ยอดต้นงวด B(k-1)": money(start),
                    "ฝากเพิ่ม d": money(d),
                    "ดอกเบี้ยงวดนี้": money(end - start - d),
                    "ยอดสิ้นงวด B(k)": money(end)})
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), hide_index=True, height=360)


# ============================================================
# ส่วนที่ 4 : หน้าจอโปรแกรม
# ============================================================
st.set_page_config(page_title="Deep Ocean Savings", page_icon="🐋", layout="wide")

# 4.1 โหลดธีม (style.css) + ฟองอากาศ
css_file = Path(__file__).with_name("style.css")
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

BUBBLES = [(4, 10, 14, 0), (11, 18, 19, 3), (19, 8, 12, 6), (27, 14, 17, 1), (36, 6, 11, 8),
           (45, 20, 22, 4), (53, 9, 13, 2), (61, 16, 18, 7), (70, 7, 12, 5), (78, 22, 24, 1),
           (86, 11, 15, 9), (93, 15, 20, 3)]  # (ตำแหน่งซ้าย %, ขนาด px, ระยะเวลา s, หน่วง s)
st.markdown('<div class="bubbles">' + "".join(
    f'<span class="bubble" style="left:{l}%;width:{s}px;height:{s}px;'
    f'animation-duration:{t}s;animation-delay:{dl}s"></span>' for l, s, t, dl in BUBBLES
) + "</div>", unsafe_allow_html=True)

# 4.2 หัวโปรแกรม
st.markdown(
    '<div class="hero"><div class="whale">🐋</div><h1>Deep Ocean Savings</h1>'
    '<p>โปรแกรมคำนวณเงินฝากแบบดอกเบี้ยทบต้น · ฝากเพิ่มต้นงวด · AM200</p>'
    f'<span class="rate-badge">🏦 ธนาคารกำหนดดอกเบี้ย {ANNUAL_RATE * 100:g}% ต่อปี (ทบต้น)</span></div>',
    unsafe_allow_html=True)
st.write("")

# 4.3 ปุ่มเลือก เงินฝาก / เงินกู้
if "mode" not in st.session_state:
    st.session_state.mode = "deposit"


def set_mode(m):
    st.session_state.mode = m


c1, c2 = st.columns(2)
c1.button("💰  เงินฝาก", width="stretch", on_click=set_mode, args=("deposit",),
          type="primary" if st.session_state.mode == "deposit" else "secondary")
c2.button("🏦  เงินกู้", width="stretch", on_click=set_mode, args=("loan",),
          type="primary" if st.session_state.mode == "loan" else "secondary")


# ---------------- หน้า "คำนวณเงินออม" ----------------
def deposit_page():
    with st.container(border=True):
        st.markdown('<div class="step-title">🐠 โปรแกรมขอถาม 4 ข้อ</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            P = st.number_input("① ต้องการฝากเงินต้น P เท่าไหร่ (บาท)", min_value=0.0,
                                value=10000.0, step=1000.0, format="%.2f", key="dep_P")
            years = st.number_input("② ฝากแบบไม่ถอนเลยกี่ปี", min_value=1, max_value=100,
                                    value=10, step=1, key="dep_years")
        with col2:
            freq = st.radio("③ จะฝากเพิ่มทุกเดือนหรือทุกปี", [FREQ_YEAR, FREQ_MONTH],
                            horizontal=True, key="dep_freq")
            per = "ปีละ" if freq == FREQ_YEAR else "เดือนละ"
            d = st.number_input(f"④ ฝากเพิ่มต้นงวด d {per}เท่าไหร่ (บาท)", min_value=0.0,
                                value=5000.0, step=500.0, format="%.2f", key="dep_d")
        if st.button("🔱  คำนวณ", type="primary", width="stretch", key="dep_go"):
            st.session_state.dep_result = dict(P=P, years=int(years), freq=freq, d=d)

    res = st.session_state.get("dep_result")
    if res is None:
        note("กรอกข้อมูลแล้วกด <b>คำนวณ</b> ได้เลย ถามใหม่กี่รอบก็ได้ 🐬")
        return
    if res != dict(P=P, years=int(years), freq=freq, d=d):
        note("✏️ ข้อมูลเปลี่ยนแล้ว กด <b>คำนวณ</b> อีกครั้งเพื่อดูคำตอบใหม่ (ด้านล่างคือคำตอบของคำถามล่าสุด)")
    show_deposit_result(**res)


def show_deposit_result(P, years, freq, d):
    r, n = rate_and_periods(years, freq)
    unit = "ปี" if freq == FREQ_YEAR else "เดือน"
    per = "ปีละ" if freq == FREQ_YEAR else "เดือนละ"

    B = balance(P, r, d, n)          # <-- ใช้สูตรหลักคำนวณคำตอบ
    paid = P + n * d
    interest = B - paid

    st.markdown("### 🐚 คำตอบ")
    st.caption(f"คำถาม: เงินต้น {money(P)} บาท · ไม่ถอน {years} ปี · ฝากเพิ่มต้นงวด {per} {money(d)} บาท")
    show_cards(
        card(f"ยอดเงินเมื่อครบ {years} ปี (B<sub>n</sub>)", f"{money(B)} บาท", f"n = {n} งวด ({unit})", "main"),
        card("เงินที่ฝากเข้าไปทั้งหมด", f"{money(paid)} บาท", f"P + n·d = {money(P)} + {n}×{money(d)}"),
        card("ดอกเบี้ยที่ได้", f"{money(interest)} บาท", "B<sub>n</sub> − (P + n·d)", "gold"),
    )

    # สูตรและการแทนค่า
    st.markdown("#### 📐 สูตรที่ใช้ (หาด้วยมือจากสมการเวียนเกิด)")
    st.latex(r"B_n=(1+r)\,(B_{n-1}+d),\quad B_0=P")
    st.latex(r"B_n=\left(P+\frac{(1+r)d}{r}\right)(1+r)^n-\frac{(1+r)d}{r}")
    r_text = short(r) if freq == FREQ_YEAR else rf"\frac{{{ANNUAL_RATE:g}}}{{12}}\approx {short(r)}"
    if r == 0:
        st.latex(rf"r=0 \;\Rightarrow\; B_{{{n}}}=P+nd={tex(B)}")
    else:
        A = (1 + r) * d / r
        st.latex(
            r"\begin{aligned}"
            rf"r&={r_text},\qquad n={n}\\"
            rf"\frac{{(1+r)d}}{{r}}&=\frac{{({short(1 + r)})({tex(d)})}}{{{short(r)}}}={tex(A)}\\"
            rf"B_{{{n}}}&=\left({tex(P)}+{tex(A)}\right)({short(1 + r)})^{{{n}}}\\"
            rf"&\quad-{tex(A)}\\"
            rf"&={tex(B)}"
            r"\end{aligned}")
        if freq == FREQ_MONTH:
            st.caption("ตัวเลขระหว่างทางแสดงแบบปัดเศษ แต่โปรแกรมคำนวณด้วยค่าเต็มทุกตำแหน่ง")
    check = balance_by_recurrence(P, r, d, n)
    if abs(check - B) < 0.005:
        note(f"✅ ตรวจด้วยสมการเวียนเกิดทีละงวด {n} รอบ ได้ {money(check)} บาท <b>ตรงกับสูตร</b>", "ok")

    st.markdown("#### 📈 เงินโตขึ้นทุกงวด")
    growth_chart(growth_table(P, r, d, n), unit)

    with st.expander("📋 ตารางยอดเงินรายงวด"):
        show_table(P, r, d, n, freq)


# ---------------- หน้า "ตั้งเป้าหมาย" ----------------
GOAL_FIND_D = "ฉันมีเงินต้นแล้ว → ต้องฝากเพิ่มงวดละเท่าไหร่ (หา d)"
GOAL_FIND_P = "ฉันรู้ว่าฝากเพิ่มได้งวดละเท่าไหร่ → ต้องมีเงินต้นเท่าไหร่ (หา P)"
GOAL_EQUAL = "เงินต้นเท่ากับเงินฝากเพิ่ม (P = d) แบบตัวอย่างอาจารย์ → งวดละเท่าไหร่"


def goal_page():
    with st.container(border=True):
        st.markdown('<div class="step-title">🎯 อยากได้เงินเท่าไหร่ ให้โปรแกรมหาว่าต้องฝากเท่าไหร่</div>',
                    unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            G = st.number_input("เป้าหมายเงิน G (บาท)", min_value=1.0, value=100000.0,
                                step=10000.0, format="%.2f", key="goal_G")
            years = st.number_input("ฝากแบบไม่ถอนเลยกี่ปี", min_value=1, max_value=100,
                                    value=10, step=1, key="goal_years")
            freq = st.radio("ฝากเพิ่มทุกเดือนหรือทุกปี", [FREQ_YEAR, FREQ_MONTH],
                            horizontal=True, key="goal_freq")
        with col2:
            find = st.radio("อยากให้โปรแกรมหาอะไร", [GOAL_FIND_D, GOAL_FIND_P, GOAL_EQUAL], key="goal_find")
            per = "ปีละ" if freq == FREQ_YEAR else "เดือนละ"
            known = 0.0
            if find == GOAL_FIND_D:
                known = st.number_input("เงินต้นที่มี P (บาท)", min_value=0.0, value=10000.0,
                                        step=1000.0, format="%.2f", key="goal_P")
            elif find == GOAL_FIND_P:
                known = st.number_input(f"ฝากเพิ่มต้นงวดได้ {per} d (บาท)", min_value=0.0,
                                        value=5000.0, step=500.0, format="%.2f", key="goal_d")
        if st.button("🎯  หาคำตอบ", type="primary", width="stretch", key="goal_go"):
            st.session_state.goal_result = dict(G=G, years=int(years), freq=freq, find=find, known=known)

    res = st.session_state.get("goal_result")
    if res is None:
        note("ตั้งเป้าหมายแล้วกด <b>หาคำตอบ</b> ได้เลย 🐳")
        return
    if res != dict(G=G, years=int(years), freq=freq, find=find, known=known):
        note("✏️ ข้อมูลเปลี่ยนแล้ว กด <b>หาคำตอบ</b> อีกครั้งเพื่อดูคำตอบใหม่")
    show_goal_result(**res)


def show_goal_result(G, years, freq, find, known):
    r, n = rate_and_periods(years, freq)
    unit = "ปี" if freq == FREQ_YEAR else "เดือน"
    per = "ปีละ" if freq == FREQ_YEAR else "เดือนละ"
    kn, F = (1 + r) ** n, deposit_factor(r, n)

    st.markdown("### 🐚 คำตอบ")
    st.caption(f"เป้าหมาย {money(G)} บาท ภายใน {years} ปี (n = {n} งวด) · ดอกเบี้ย {ANNUAL_RATE * 100:g}% ต่อปี")

    # 1) ใช้สูตรที่ย้ายข้างแล้วหาคำตอบ
    if find == GOAL_FIND_D:
        P, d_raw = known, need_d(G, known, r, n)
        formula = r"d=\dfrac{G-P(1+r)^n}{(1+r)\dfrac{(1+r)^n-1}{r}}"
        d = round_up(max(d_raw, 0.0))
        if d_raw <= 0:
            note(f"🎉 เงินต้น {money(P)} บาทอย่างเดียวก็ถึงเป้าแล้ว ไม่ต้องฝากเพิ่มเลย", "ok")
        main = card(f"ต้องฝากเพิ่มต้นงวด {per}", f"{money(d)} บาท", "ปัดขึ้นเป็นสตางค์ให้ถึงเป้าแน่นอน", "main")
    elif find == GOAL_FIND_P:
        d, P_raw = known, need_P(G, known, r, n)
        formula = r"P=\dfrac{G-d(1+r)\dfrac{(1+r)^n-1}{r}}{(1+r)^n}"
        P = round_up(max(P_raw, 0.0))
        if P_raw <= 0:
            note(f"🎉 ฝากเพิ่ม{per} {money(d)} บาทอย่างเดียวก็ถึงเป้าแล้ว ไม่ต้องมีเงินต้นเลย", "ok")
        main = card("ต้องมีเงินต้น P", f"{money(P)} บาท", "ปัดขึ้นเป็นสตางค์ให้ถึงเป้าแน่นอน", "main")
    else:
        x = round_up(need_equal(G, r, n))
        P = d = x
        formula = r"P=d=\dfrac{G}{(1+r)^n+(1+r)\dfrac{(1+r)^n-1}{r}}"
        main = card(f"เงินต้น และฝากเพิ่มต้นงวด {per}", f"{money(x)} บาท", "P = d (ปัดขึ้นเป็นสตางค์)", "main")

    # 2) แทนค่ากลับในสูตรหลักเพื่อยืนยัน
    B = balance(P, r, d, n)
    paid = P + n * d
    show_cards(main,
               card("เงินที่ฝากเข้าไปทั้งหมด", f"{money(paid)} บาท", "P + n·d"),
               card("ดอกเบี้ยที่ได้", f"{money(B - paid)} บาท", f"ยอดสุดท้าย {money(B)} บาท", "gold"))

    st.markdown("#### 📐 สูตร (ย้ายข้างจากสูตรหลัก โดยให้ B<sub>n</sub> = G)", unsafe_allow_html=True)
    st.latex(r"G=\left(P+\frac{(1+r)d}{r}\right)(1+r)^n-\frac{(1+r)d}{r}")
    st.latex(r"\phantom{G}=P(1+r)^n+d(1+r)\frac{(1+r)^n-1}{r}")
    st.latex(formula)
    st.latex(rf"(1+r)^{{{n}}}={kn:.6f}")
    st.latex(rf"(1+r)\frac{{(1+r)^{{{n}}}-1}}{{r}}={F:.6f}")
    if B >= G - 0.005:
        note(f"✅ แทนค่ากลับในสูตรหลัก ได้ B<sub>{n}</sub> = {money(B)} บาท ≥ เป้าหมาย {money(G)} บาท", "ok")

    st.markdown("#### 📈 เส้นทางสู่เป้าหมาย")
    growth_chart(growth_table(P, r, d, n), unit, goal=G)

    with st.expander("📋 ตารางยอดเงินรายงวด"):
        show_table(P, r, d, n, freq)


# ---------------- หน้า "เงินกู้" (ยังไม่เปิดใช้) ----------------
def loan_page():
    st.markdown(
        '<div class="ocean-card" style="text-align:center;padding:42px 20px;margin-top:10px">'
        '<div style="font-size:3rem">🛠️🐙</div>'
        '<div class="value" style="font-size:1.5rem">เงินกู้ — กำลังพัฒนา</div>'
        '<div class="sub" style="font-size:1rem;margin-top:8px">'
        'เร็ว ๆ นี้: คำนวณค่างวดผ่อนต่อเดือน/ต่อปี แบบลดต้นลดดอก</div></div>',
        unsafe_allow_html=True)


# 4.4 แสดงหน้าตามปุ่มที่เลือก
st.write("")
if st.session_state.mode == "deposit":
    tab_calc, tab_goal = st.tabs(["🌊  คำนวณเงินออม", "🎯  ตั้งเป้าหมาย"])
    with tab_calc:
        deposit_page()
    with tab_goal:
        goal_page()
else:
    loan_page()

st.markdown('<p style="text-align:center;color:#5f8fa8;margin-top:2.5rem">'
            'AM200 · Recurrence Relation · ทุกคำตอบคำนวณจากสูตรทั่วไปที่หาด้วยมือ 🐋</p>',
            unsafe_allow_html=True)
