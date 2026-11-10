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
DEPOSIT_RATE = 0.02  # ดอกเบี้ยเงินฝาก 2% ต่อปี แบบทบต้น (แก้ตรงนี้ที่เดียว ทั้งโปรแกรมเปลี่ยนตาม)
LOAN_RATE = 0.12     # ดอกเบี้ยเงินกู้ 12% ต่อปี แบบลดต้นลดดอก

FREQ_YEAR = "ทุกปี"
FREQ_MONTH = "ทุกเดือน"

PAY_MONTH = "ผ่อนรายเดือน"
PAY_YEAR = "ผ่อนรายปี"


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
        return DEPOSIT_RATE / 12, years * 12
    return DEPOSIT_RATE, years


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


# --- เงินกู้ แบบลดต้นลดดอก ผ่อนเท่ากันทุกงวด จ่ายปลายงวด ---
#   L = เงินกู้, i = ดอกเบี้ยต่องวด, X = ค่างวด, N = จำนวนงวด
#   A_n = หนี้คงเหลือหลังจ่ายงวดที่ n
def loan_rate_and_periods(years, freq):
    """ผ่อนรายเดือน : i = LOAN_RATE / 12, N = 12 x จำนวนปี
    ผ่อนรายปี   : i = LOAN_RATE,      N = จำนวนปี
    """
    if freq == PAY_MONTH:
        return LOAN_RATE / 12, years * 12
    return LOAN_RATE, years


def loan_payment(L, i, N):
    """สูตรค่างวด (หาด้วยมือจากสมการเวียนเกิด โดยให้ A_N = 0)
        X = L·i·(1+i)^N / ((1+i)^N - 1)
    """
    if i == 0:  # ไม่มีดอกเบี้ย -> แบ่งเงินต้นเท่า ๆ กัน
        return L / N
    k = (1 + i) ** N
    return L * i * k / (k - 1)


def loan_by_recurrence(L, i, X, N):
    """วนสมการเวียนเกิดทีละงวด  A_n = (1+i)A_{n-1} - X,  A_0 = L
    คืนค่ารายการ (ดอกเบี้ยงวดนี้, ส่วนที่ไปลดเงินต้น, หนี้คงเหลือ) ของงวดที่ 1..N
    """
    rows, A = [], L
    for _ in range(N):
        interest = i * A          # ดอกเบี้ยคิดจากหนี้ที่ยังเหลือ (ลดต้นลดดอก)
        A = (1 + i) * A - X       # สมการเวียนเกิด
        rows.append((interest, X - interest, A))
    return rows


# --- สูตรสำหรับ "ตั้งเป้าหมาย" ฝั่งเงินกู้ : ย้ายข้างจากเงื่อนไข A_N = 0 ---
def loan_left(L, i, X, n):
    """สูตรทั่วไป: หนี้คงเหลือหลังจ่ายงวดที่ n
        A_n = (1+i)^n L - X((1+i)^n - 1)/i
    """
    if i == 0:
        return L - n * X
    k = (1 + i) ** n
    return k * L - X * (k - 1) / i


def loan_max(X, i, N):
    """ผ่อนได้งวดละ X  ->  กู้ได้สูงสุดเท่าไหร่
        L = X(1 - (1+i)^(-N)) / i
    """
    if i == 0:  # ไม่มีดอกเบี้ย -> L = X·N
        return X * N
    return X * (1 - (1 + i) ** (-N)) / i


def loan_periods(L, i, X):
    """กู้ L ผ่อนงวดละ X  ->  จำนวนงวด N* (ยังไม่ปัด)
        (1+i)^N = X / (X - L·i)   =>   N* = ln(X / (X - L·i)) / ln(1+i)
    ใช้ได้เมื่อ X > L·i เท่านั้น (ถ้าไม่ใช่ จ่ายแค่ดอกเบี้ย หนี้ไม่ลดเลย)
    """
    if i == 0:
        return L / X
    return math.log(X / (X - L * i)) / math.log(1 + i)


def whole_periods(N_star):
    """จำนวนงวดจริง = ปัดขึ้นของ N*  (ถ้า N* เป็นจำนวนเต็มอยู่แล้ว ไม่ต้องปัด)"""
    nearest = round(N_star)
    if abs(N_star - nearest) < 1e-9:  # กันเศษทศนิยมเล็ก ๆ เช่น 359.9999999999
        return max(int(nearest), 1)
    return max(math.ceil(N_star), 1)


def loan_payoff(L, i, X, N):
    """ใช้ "ตรวจคำตอบ": วนสมการเวียนเกิด A_n = (1+i)A_{n-1} - X ทีละงวด
    โดยงวดสุดท้าย (งวดที่ N) จ่ายแค่ที่เหลือ = (1+i)·A_{N-1}
    คืนค่า (รายการแต่ละงวดแบบเดียวกับ loan_by_recurrence, ค่างวดสุดท้าย)
    """
    rows = loan_by_recurrence(L, i, X, N - 1)
    A = rows[-1][2] if rows else L
    interest = i * A
    last = (1 + i) * A
    rows.append((interest, last - interest, (1 + i) * A - last))
    return rows, last


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


def round_down(x):
    """ปัดลงเป็นสตางค์ (ใช้กับ "วงเงินกู้สูงสุด" เพื่อไม่ให้เกินที่ผ่อนไหว)"""
    return math.floor(x * 100 + 1e-9) / 100


def years_months(N, freq):
    """จำนวนงวด -> ข้อความ เช่น 162 งวดรายเดือน -> '13 ปี 6 เดือน'"""
    if freq == PAY_YEAR:
        return f"{N} ปี"
    y, m = divmod(N, 12)
    parts = ([f"{y} ปี"] if y else []) + ([f"{m} เดือน"] if m else [])
    return " ".join(parts)


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


def zero_if_tiny(x):
    """เศษเล็กมากจากการคำนวณทศนิยม (เช่น -0.000000001) ให้แสดงเป็น 0"""
    return 0.0 if abs(x) < 0.005 else x


def loan_chart(df, unit):
    """กราฟหนี้คงเหลือลดลงทุกงวด (ธีมแมกมา)"""
    x = alt.X("งวดที่:Q", title=f"งวดที่ ({unit})", axis=alt.Axis(format="d", tickMinStep=1))
    y = alt.Y("หนี้คงเหลือ:Q", title="บาท", axis=alt.Axis(format=",.0f"))

    lava = alt.Chart(df).mark_area(
        color=alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                           stops=[alt.GradientStop(color="rgba(255,77,46,0.03)", offset=0),
                                  alt.GradientStop(color="rgba(255,120,40,0.55)", offset=1)])
    ).encode(x=x, y=y)

    line = alt.Chart(df).mark_line(strokeWidth=2.8, color="#FFB347").encode(
        x=x, y=y,
        tooltip=[alt.Tooltip("งวดที่:Q"), alt.Tooltip("หนี้คงเหลือ:Q", format=",.2f")],
    )

    chart = (alt.layer(lava, line).properties(height=340)
             .configure(background="transparent")
             .configure_view(strokeWidth=0)
             .configure_axis(labelColor="#ffc9a8", titleColor="#ffc9a8",
                             gridColor="rgba(255,255,255,0.08)", domainColor="#a8402a"))
    st.altair_chart(chart, theme=None, width="stretch")


def loan_compare_chart(df, unit):
    """กราฟหนี้คงเหลือ 2 เส้น: ผ่อนตามปกติ vs โปะเพิ่ม (ธีมแมกมา)"""
    series = list(df["รายการ"].unique())
    x = alt.X("งวดที่:Q", title=f"งวดที่ ({unit})", axis=alt.Axis(format="d", tickMinStep=1))
    lines = alt.Chart(df).mark_line(strokeWidth=2.8).encode(
        x=x,
        y=alt.Y("หนี้คงเหลือ:Q", title="บาท", axis=alt.Axis(format=",.0f")),
        color=alt.Color("รายการ:N", scale=alt.Scale(domain=series, range=["#FFB347", "#FF4D2E"]),
                        legend=alt.Legend(title=None, orient="top")),
        strokeDash=alt.StrokeDash("รายการ:N", scale=alt.Scale(domain=series, range=[[6, 4], [1, 0]]),
                                  legend=None),
        tooltip=[alt.Tooltip("งวดที่:Q"), alt.Tooltip("รายการ:N"),
                 alt.Tooltip("หนี้คงเหลือ:Q", format=",.2f")],
    )
    chart = (lines.properties(height=340)
             .configure(background="transparent")
             .configure_view(strokeWidth=0)
             .configure_axis(labelColor="#ffc9a8", titleColor="#ffc9a8",
                             gridColor="rgba(255,255,255,0.08)", domainColor="#a8402a")
             .configure_legend(labelColor="#ffe0cc", labelFontSize=13))
    st.altair_chart(chart, theme=None, width="stretch")


def show_loan_table(rows, X, freq, last=None):
    """ตารางผ่อนรายงวด: ค่างวด = ดอกเบี้ย + ส่วนลดเงินต้น
    last = ค่างวดสุดท้าย (ถ้างวดสุดท้ายจ่ายน้อยกว่า X) ไม่ใส่ = ทุกงวดจ่าย X เท่ากัน
    """
    data = []
    for k, (interest, principal, left) in enumerate(rows, start=1):
        row = {"งวดที่": k}
        if freq == PAY_MONTH:
            row["ปีที่"] = math.ceil(k / 12)
        pay = last if (last is not None and k == len(rows)) else X
        row.update({"ค่างวด X": money(pay),
                    "ดอกเบี้ย": money(interest),
                    "ส่วนลดเงินต้น": money(principal),
                    "หนี้คงเหลือ A(k)": money(zero_if_tiny(left))})
        data.append(row)
    # ตารางวาดบน canvas จึงแต่งด้วย CSS ไม่ได้ -> ใช้ Styler ของ pandas ระบายสีช่องเป็นโทนแมกมา
    styled = pd.DataFrame(data).style.set_properties(
        **{"background-color": "#2a0907", "color": "#ffe0cc"})
    st.dataframe(styled, hide_index=True, height=360)


# ============================================================
# ส่วนที่ 4 : หน้าจอโปรแกรม
# ============================================================
st.set_page_config(page_title="Deep Ocean Savings", page_icon="🐋", layout="wide")

# 4.1 โหลดธีม (style.css) + ฟองอากาศ
css_file = Path(__file__).with_name("style.css")
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# อยู่หน้าเงินกู้ -> โหลดธีมแมกมา (magma.css) ทับธีมมหาสมุทร และเปลี่ยนฟองอากาศเป็นประกายไฟ
is_loan = st.session_state.get("mode") == "loan"
magma_file = Path(__file__).with_name("magma.css")
if is_loan and magma_file.exists():
    st.markdown(f"<style>{magma_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)
bubble_class = "bubble ember" if is_loan else "bubble"

BUBBLES = [(4, 10, 14, 0), (11, 18, 19, 3), (19, 8, 12, 6), (27, 14, 17, 1), (36, 6, 11, 8),
           (45, 20, 22, 4), (53, 9, 13, 2), (61, 16, 18, 7), (70, 7, 12, 5), (78, 22, 24, 1),
           (86, 11, 15, 9), (93, 15, 20, 3)]  # (ตำแหน่งซ้าย %, ขนาด px, ระยะเวลา s, หน่วง s)
st.markdown('<div class="bubbles">' + "".join(
    f'<span class="{bubble_class}" style="left:{l}%;width:{s}px;height:{s}px;'
    f'animation-duration:{t}s;animation-delay:{dl}s"></span>' for l, s, t, dl in BUBBLES
) + "</div>", unsafe_allow_html=True)

# 4.2 หัวโปรแกรม
st.markdown(
    '<div class="hero"><div class="whale">🐋</div><h1>Deep Ocean Savings</h1>'
    '<p>โปรแกรมคำนวณเงินฝากแบบดอกเบี้ยทบต้น · ฝากเพิ่มต้นงวด · AM200</p>'
    f'<span class="rate-badge">🏦 ดอกเบี้ยเงินฝาก {DEPOSIT_RATE * 100:g}% ต่อปี (ทบต้น)'
    f' · 💳 ดอกเบี้ยเงินกู้ {LOAN_RATE * 100:g}% ต่อปี</span></div>',
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
    r_text = short(r) if freq == FREQ_YEAR else rf"\frac{{{DEPOSIT_RATE:g}}}{{12}}\approx {short(r)}"
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
GOAL_FIND_D = "ฉันมีเงินต้นแล้ว → จะต้องฝากเพิ่มงวดละเท่าไหร่ (หา d)"
GOAL_FIND_P = "ฉันรู้ว่าฝากเพิ่มได้งวดละเท่าไหร่ → จะต้องมีเงินต้นเท่าไหร่ (หา P)"
GOAL_EQUAL = "เงินต้นเท่ากับเงินฝากเพิ่ม (P = d) → จะต้องเพิ่มงวดละเท่าไหร่"


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
    st.caption(f"เป้าหมาย {money(G)} บาท ภายใน {years} ปี (n = {n} งวด) · ดอกเบี้ย {DEPOSIT_RATE * 100:g}% ต่อปี")

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


# ---------------- หน้า "เงินกู้" (ลดต้นลดดอก ผ่อนเท่ากันทุกงวด จ่ายปลายงวด) ----------------
def loan_page():
    with st.container(border=True):
        st.markdown('<div class="step-title">🌋 โปรแกรมขอถาม 3 ข้อ</div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            L = st.number_input("① ต้องการกู้เงิน L เท่าไหร่ (บาท)", min_value=1.0,
                                value=4000000.0, step=100000.0, format="%.2f", key="loan_L")
            years = st.number_input("② ผ่อนกี่ปี", min_value=1, max_value=100,
                                    value=30, step=1, key="loan_years")
        with col2:
            freq = st.radio("③ จะผ่อนรายเดือนหรือรายปี", [PAY_MONTH, PAY_YEAR],
                            horizontal=True, key="loan_freq")
        if st.button("🔥  คำนวณค่างวด", type="primary", width="stretch", key="loan_go"):
            st.session_state.loan_result = dict(L=L, years=int(years), freq=freq)

    res = st.session_state.get("loan_result")
    if res is None:
        note("กรอกข้อมูลแล้วกด <b>คำนวณค่างวด</b> ได้เลย 🌋")
        return
    if res != dict(L=L, years=int(years), freq=freq):
        note("✏️ ข้อมูลเปลี่ยนแล้ว กด <b>คำนวณค่างวด</b> อีกครั้งเพื่อดูคำตอบใหม่ (ด้านล่างคือคำตอบของคำถามล่าสุด)")
    show_loan_result(**res)


def show_loan_result(L, years, freq):
    i, N = loan_rate_and_periods(years, freq)
    unit = "เดือน" if freq == PAY_MONTH else "ปี"
    per = "เดือนละ" if freq == PAY_MONTH else "ปีละ"

    X = loan_payment(L, i, N)        # <-- ใช้สูตรที่หาด้วยมือคำนวณค่างวด
    total = N * X
    interest = total - L

    st.markdown("### 🔥 คำตอบ")
    st.caption(f"คำถาม: กู้ {money(L)} บาท · ผ่อน {years} ปี · {freq} · "
               f"ดอกเบี้ยเงินกู้ {LOAN_RATE * 100:g}% ต่อปี")
    show_cards(
        card(f"ค่างวดที่ต้องผ่อน{per} (X)", f"{money(X)} บาท", f"N = {N} งวด ({unit}) · จ่ายปลายงวด", "main"),
        card("ยอดจ่ายรวมทั้งหมด", f"{money(total)} บาท", f"N·X = {N}×{money(X)}"),
        card("ดอกเบี้ยที่ต้องจ่ายรวม", f"{money(interest)} บาท", "N·X − L", "gold"),
    )

    # สูตรและการแทนค่า
    st.markdown("#### 📐 สูตรที่ใช้ (หาด้วยมือจากสมการเวียนเกิด)")
    st.latex(r"A_n=(1+i)\,A_{n-1}-X,\quad A_0=L")
    st.latex(r"A_N=0\;\Rightarrow\;X=\frac{L\,i\,(1+i)^N}{(1+i)^N-1}")
    if i == 0:
        st.latex(rf"i=0 \;\Rightarrow\; X=\frac{{L}}{{N}}=\frac{{{tex(L)}}}{{{N}}}={tex(X)}")
    else:
        k = (1 + i) ** N
        i_text = short(i) if freq == PAY_YEAR else rf"\frac{{{LOAN_RATE:g}}}{{12}}={short(i)}"
        st.latex(
            r"\begin{aligned}"
            rf"i&={i_text},\qquad N={N}\\"
            rf"(1+i)^N&=({short(1 + i)})^{{{N}}}\approx {k:.6f}\\"
            rf"X&=\frac{{({tex(L)})({short(i)})({k:.6f})}}{{{k:.6f}-1}}\\"
            rf"&={tex(X)}"
            r"\end{aligned}")
        st.caption("ตัวเลขระหว่างทางแสดงแบบปัดเศษ แต่โปรแกรมคำนวณด้วยค่าเต็มทุกตำแหน่ง")

    rows = loan_by_recurrence(L, i, X, N)
    left = rows[-1][2]
    if abs(left) < 0.005:
        note(f"✅ ตรวจด้วยสมการเวียนเกิดทีละงวด {N} รอบ หนี้เหลือ {money(zero_if_tiny(left))} บาท "
             f"<b>ผ่อนหมดพอดี</b>", "ok")

    st.markdown("#### 📉 หนี้คงเหลือลดลงทุกงวด")
    df = pd.DataFrame({"งวดที่": range(N + 1),
                       "หนี้คงเหลือ": [L] + [zero_if_tiny(r[2]) for r in rows]})
    loan_chart(df, unit)

    with st.expander("📋 ตารางผ่อนรายงวด"):
        show_loan_table(rows, X, freq)


# ---------------- หน้า "ตั้งเป้าหมาย" ฝั่งเงินกู้ ----------------
LGOAL_FIND_L = "ผ่อนได้งวดละ X → กู้ได้สูงสุดเท่าไหร่ (หา L)"
LGOAL_FIND_N = "กู้ L ผ่อนได้งวดละ X → ต้องผ่อนกี่งวดถึงหมด (หา N)"
LGOAL_EXTRA = "โปะเพิ่มงวดละ E → หมดเร็วขึ้นกี่งวด ประหยัดดอกเบี้ยเท่าไหร่"
MAX_PERIODS = 6000  # กันกรณีจำนวนงวดมหาศาล (ตาราง/กราฟจะช้ามาก)


def loan_goal_page():
    with st.container(border=True):
        st.markdown('<div class="step-title">🎯 บอกสิ่งที่รู้ ให้โปรแกรมหาส่วนที่เหลือ</div>',
                    unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            find = st.radio("อยากให้โปรแกรมหาอะไร", [LGOAL_FIND_L, LGOAL_FIND_N, LGOAL_EXTRA], key="lg_find")
            freq = st.radio("จะผ่อนรายเดือนหรือรายปี", [PAY_MONTH, PAY_YEAR], horizontal=True, key="lg_freq")
        with col2:
            per = "เดือนละ" if freq == PAY_MONTH else "ปีละ"
            if find == LGOAL_FIND_L:
                values = dict(
                    X=st.number_input(f"ผ่อนได้{per} X (บาท)", min_value=1.0, value=20000.0,
                                      step=1000.0, format="%.2f", key="lg1_X"),
                    years=int(st.number_input("ผ่อนกี่ปี", min_value=1, max_value=100,
                                              value=30, step=1, key="lg1_years")))
            elif find == LGOAL_FIND_N:
                values = dict(
                    L=st.number_input("กู้เงิน L (บาท)", min_value=1.0, value=4000000.0,
                                      step=100000.0, format="%.2f", key="lg2_L"),
                    X=st.number_input(f"ผ่อนได้{per} X (บาท)", min_value=1.0, value=50000.0,
                                      step=1000.0, format="%.2f", key="lg2_X"))
            else:
                values = dict(
                    L=st.number_input("กู้เงิน L (บาท)", min_value=1.0, value=4000000.0,
                                      step=100000.0, format="%.2f", key="lg3_L"),
                    years=int(st.number_input("สัญญาผ่อนกี่ปี", min_value=1, max_value=100,
                                              value=30, step=1, key="lg3_years")),
                    E=st.number_input(f"โปะเพิ่ม{per} E (บาท)", min_value=0.0, value=10000.0,
                                      step=1000.0, format="%.2f", key="lg3_E"))
        if st.button("🎯  หาคำตอบ", type="primary", width="stretch", key="lg_go"):
            st.session_state.loan_goal_result = dict(find=find, freq=freq, **values)

    res = st.session_state.get("loan_goal_result")
    if res is None:
        note("เลือกสิ่งที่อยากรู้ กรอกข้อมูล แล้วกด <b>หาคำตอบ</b> ได้เลย 🌋")
        return
    if res != dict(find=find, freq=freq, **values):
        note("✏️ ข้อมูลเปลี่ยนแล้ว กด <b>หาคำตอบ</b> อีกครั้งเพื่อดูคำตอบใหม่ (ด้านล่างคือคำตอบของคำถามล่าสุด)")
    show_loan_goal_result(**res)


def loan_i_latex(i, freq):
    """ข้อความ i สำหรับใส่ในสูตร เช่น  0.12/12 = 0.01"""
    return short(i) if freq == PAY_YEAR else rf"\frac{{{LOAN_RATE:g}}}{{12}}={short(i)}"


def show_loan_goal_result(find, freq, **v):
    st.markdown("### 🔥 คำตอบ")
    if find == LGOAL_FIND_L:
        show_find_L(v["X"], v["years"], freq)
    elif find == LGOAL_FIND_N:
        show_find_N(v["L"], v["X"], freq)
    else:
        show_extra(v["L"], v["years"], v["E"], freq)


# แบบที่ 1 : หา L
def show_find_L(X, years, freq):
    i, N = loan_rate_and_periods(years, freq)
    unit = "เดือน" if freq == PAY_MONTH else "ปี"
    per = "เดือนละ" if freq == PAY_MONTH else "ปีละ"

    L_raw = loan_max(X, i, N)        # <-- สูตรที่ย้ายข้างจาก A_N = 0
    L = round_down(L_raw)
    total = N * X

    st.caption(f"คำถาม: ผ่อนได้{per} {money(X)} บาท · {years} ปี · {freq} · "
               f"ดอกเบี้ยเงินกู้ {LOAN_RATE * 100:g}% ต่อปี")
    show_cards(
        card("กู้ได้สูงสุด (L)", f"{money(L)} บาท", "ปัดลงเป็นสตางค์ ไม่ให้เกินที่ผ่อนไหว", "main"),
        card("ยอดจ่ายรวมทั้งหมด", f"{money(total)} บาท", f"N·X = {N}×{money(X)}"),
        card("ดอกเบี้ยที่ต้องจ่ายรวม", f"{money(total - L)} บาท", "N·X − L", "gold"),
    )

    st.markdown("#### 📐 สูตร (ย้ายข้างจากสูตรทั่วไป โดยให้ A<sub>N</sub> = 0)", unsafe_allow_html=True)
    st.latex(r"A_N=(1+i)^N L-X\,\frac{(1+i)^N-1}{i}=0")
    st.latex(r"\Rightarrow\;L=\frac{X\left(1-(1+i)^{-N}\right)}{i}")
    if i == 0:
        st.latex(rf"i=0 \;\Rightarrow\; L=XN=({tex(X)})({N})={tex(L_raw)}")
    else:
        v = (1 + i) ** (-N)
        st.latex(
            r"\begin{aligned}"
            rf"i&={loan_i_latex(i, freq)},\qquad N={N}\\"
            rf"(1+i)^{{-N}}&=({short(1 + i)})^{{-{N}}}\approx {v:.6f}\\"
            rf"L&=\frac{{({tex(X)})(1-{v:.6f})}}{{{short(i)}}}\\"
            rf"&\approx {tex(L_raw)}"
            r"\end{aligned}")
        st.caption("ตัวเลขระหว่างทางแสดงแบบปัดเศษ แต่โปรแกรมคำนวณด้วยค่าเต็มทุกตำแหน่ง")

    # ตรวจ: กู้ L (ค่าเต็ม) แล้วผ่อนงวดละ X ครบ N งวด หนี้ต้องเหลือ 0
    rows = loan_by_recurrence(L_raw, i, X, N)
    left = rows[-1][2]
    if abs(left) < 0.005:
        note(f"✅ ตรวจด้วยสมการเวียนเกิด: กู้ {money(L_raw)} บาท ผ่อน{per} {money(X)} บาท ครบ {N} รอบ "
             f"หนี้เหลือ {money(zero_if_tiny(left))} บาท <b>ผ่อนหมดพอดี</b>", "ok")

    st.markdown("#### 📉 หนี้คงเหลือลดลงทุกงวด")
    df = pd.DataFrame({"งวดที่": range(N + 1),
                       "หนี้คงเหลือ": [L_raw] + [zero_if_tiny(r[2]) for r in rows]})
    loan_chart(df, unit)
    with st.expander("📋 ตารางผ่อนรายงวด"):
        show_loan_table(rows, X, freq)


def periods_latex(L, i, X, N_star, N, A_prev, last, freq):
    """แสดงการแทนค่าในสูตรหาจำนวนงวด (ใช้ทั้งแบบที่ 2 และ 3)"""
    st.latex(r"A_N=(1+i)^N L-X\,\frac{(1+i)^N-1}{i}=0")
    st.latex(r"\Rightarrow\;(1+i)^N=\frac{X}{X-L\,i}")
    st.latex(r"\Rightarrow\;N^{*}=\frac{\ln\left(\dfrac{X}{X-L\,i}\right)}{\ln(1+i)}")
    if i == 0:
        st.latex(rf"i=0 \;\Rightarrow\; N^{{*}}=\frac{{L}}{{X}}=\frac{{{tex(L)}}}{{{tex(X)}}}"
                 rf"\approx {N_star:.4f}")
    else:
        st.latex(
            r"\begin{aligned}"
            rf"i&={loan_i_latex(i, freq)}\\"
            rf"L\,i&=({tex(L)})({short(i)})={tex(L * i)}\\"
            rf"N^{{*}}&=\frac{{\ln\left(\dfrac{{{tex(X)}}}{{{tex(X)}-{tex(L * i)}}}\right)}}"
            rf"{{\ln({short(1 + i)})}}\\"
            rf"&\approx {N_star:.4f}"
            r"\end{aligned}")
    st.latex(rf"N=\lceil N^{{*}}\rceil={N}")
    st.latex(
        r"\begin{aligned}"
        rf"A_{{{N - 1}}}&\approx {tex(A_prev)}\\"
        rf"X_{{\text{{last}}}}&=(1+i)\,A_{{{N - 1}}}\\"
        rf"&\approx {tex(last)}"
        r"\end{aligned}")
    st.caption("A_(N−1) หาจากสูตรทั่วไป A_n = (1+i)ⁿL − X((1+i)ⁿ − 1)/i  · "
               "ตัวเลขระหว่างทางแสดงแบบปัดเศษ แต่โปรแกรมคำนวณด้วยค่าเต็มทุกตำแหน่ง")


def payoff_numbers(L, i, X):
    """คำตอบแบบที่ 2 จากสูตรปิด -> (N*, N, A_(N-1), งวดสุดท้าย, ยอดจ่ายรวม)"""
    N_star = loan_periods(L, i, X)
    N = whole_periods(N_star)
    A_prev = loan_left(L, i, X, N - 1)
    last = (1 + i) * A_prev
    return N_star, N, A_prev, last, (N - 1) * X + last


def check_payoff(L, i, X, N, last, per):
    """แถบ ✅ : วนสมการเวียนเกิดทีละงวด (งวดสุดท้ายจ่ายแค่ที่เหลือ) แล้วดูว่าหนี้เหลือ 0"""
    rows, last_check = loan_payoff(L, i, X, N)
    left = rows[-1][2]
    if abs(left) < 0.005 and abs(last_check - last) < 0.005 and last <= X + 0.005:
        note(f"✅ ตรวจด้วยสมการเวียนเกิด: ผ่อน{per} {money(X)} บาท {N - 1} งวด "
             f"แล้วงวดที่ {N} จ่าย {money(last)} บาท หนี้เหลือ {money(zero_if_tiny(left))} บาท "
             f"<b>ผ่อนหมดพอดี</b>", "ok")
    return rows


# แบบที่ 2 : หา N
def show_find_N(L, X, freq):
    i, _ = loan_rate_and_periods(1, freq)
    unit = "เดือน" if freq == PAY_MONTH else "ปี"
    per = "เดือนละ" if freq == PAY_MONTH else "ปีละ"
    st.caption(f"คำถาม: กู้ {money(L)} บาท · ผ่อนได้{per} {money(X)} บาท · {freq} · "
               f"ดอกเบี้ยเงินกู้ {LOAN_RATE * 100:g}% ต่อปี")

    if X <= L * i:  # ค่างวดไม่พอแม้แต่ดอกเบี้ย -> หนี้ไม่ลดลงเลย
        note(f"⛔ ผ่อน{per} {money(X)} บาท <b>ไม่มีวันหมด</b> เพราะดอกเบี้ยงวดแรกก็ "
             f"L·i = {money(L * i)} บาทแล้ว (จ่ายไปก็โดนแค่ดอกเบี้ย หนี้ไม่ลด) "
             f"ค่างวดต้อง<b>มากกว่า {money(L * i)} บาท</b>", "warn")
        return

    N_star, N, A_prev, last, total = payoff_numbers(L, i, X)
    show_cards(
        card("ต้องผ่อนทั้งหมด", f"{N} งวด", years_months(N, freq), "main"),
        card("งวดสุดท้ายจ่าย", f"{money(last)} บาท", f"งวดที่ {N} · งวดอื่นจ่าย {money(X)} บาท"),
        card("ยอดจ่ายรวมทั้งหมด", f"{money(total)} บาท", f"({N}−1)×{money(X)} + งวดสุดท้าย"),
        card("ดอกเบี้ยที่ต้องจ่ายรวม", f"{money(total - L)} บาท", "ยอดจ่ายรวม − L", "gold"),
    )

    st.markdown("#### 📐 สูตร (ย้ายข้างจากสูตรทั่วไป โดยให้ A<sub>N</sub> = 0)", unsafe_allow_html=True)
    periods_latex(L, i, X, N_star, N, A_prev, last, freq)

    if N > MAX_PERIODS:
        note(f"จำนวนงวดเยอะมาก ({N:,} งวด) จึงไม่แสดงกราฟและตาราง")
        return
    rows = check_payoff(L, i, X, N, last, per)

    st.markdown("#### 📉 หนี้คงเหลือลดลงทุกงวด")
    df = pd.DataFrame({"งวดที่": range(N + 1),
                       "หนี้คงเหลือ": [L] + [zero_if_tiny(r[2]) for r in rows]})
    loan_chart(df, unit)
    with st.expander("📋 ตารางผ่อนรายงวด"):
        show_loan_table(rows, X, freq, last=last)


# แบบที่ 3 : โปะเพิ่มงวดละ E
def show_extra(L, years, E, freq):
    i, N0 = loan_rate_and_periods(years, freq)
    unit = "เดือน" if freq == PAY_MONTH else "ปี"
    per = "เดือนละ" if freq == PAY_MONTH else "ปีละ"

    X = loan_payment(L, i, N0)       # ค่างวดเดิม (สูตรหลัก) ใช้ค่าเต็ม ไม่ปัด
    old_interest = N0 * X - L
    X_new = X + E
    N_star, N, A_prev, last, total = payoff_numbers(L, i, X_new)
    new_interest = total - L
    saved = old_interest - new_interest

    st.caption(f"คำถาม: กู้ {money(L)} บาท · สัญญา {years} ปี · {freq} · โปะเพิ่ม{per} {money(E)} บาท · "
               f"ดอกเบี้ยเงินกู้ {LOAN_RATE * 100:g}% ต่อปี")
    show_cards(
        card("หมดหนี้ใน", f"{N} งวด", f"{years_months(N, freq)} (เดิม {N0} งวด)", "main"),
        card("เร็วขึ้น", f"{N0 - N} งวด", years_months(N0 - N, freq) or "เท่าเดิม"),
        card("ประหยัดดอกเบี้ย", f"{money(saved)} บาท", "ดอกเบี้ยเดิม − ดอกเบี้ยใหม่", "gold"),
    )
    show_cards(
        card("ค่างวดเดิม → ใหม่", f"{money(X_new)} บาท", f"เดิม {money(X)} + โปะ {money(E)}"),
        card("งวดสุดท้ายจ่าย", f"{money(last)} บาท", f"งวดที่ {N}"),
        card("ดอกเบี้ยรวม เดิม → ใหม่", f"{money(new_interest)} บาท", f"เดิม {money(old_interest)} บาท"),
    )

    st.markdown("#### 📐 สูตร", unsafe_allow_html=True)
    st.markdown("**ขั้นที่ 1** หาค่างวดเดิม X จากสูตรหลัก")
    st.latex(r"X=\frac{L\,i\,(1+i)^N}{(1+i)^N-1}")
    st.latex(rf"X\approx {tex(X)},\qquad X'=X+E={tex(X)}+{tex(E)}={tex(X_new)}")
    st.markdown("**ขั้นที่ 2** ใช้สูตรหาจำนวนงวด (แบบที่ 2) โดยแทน X ด้วยค่างวดใหม่ X′")
    periods_latex(L, i, X_new, N_star, N, A_prev, last, freq)
    st.markdown("**ขั้นที่ 3** เทียบดอกเบี้ยรวม")
    st.latex(
        r"\begin{aligned}"
        rf"\text{{old}}&=N_0X-L={N0}({tex(X)})-{tex(L)}\\"
        rf"&\approx {tex(old_interest)}\\"
        rf"\text{{new}}&=(N-1)X'+X_{{\text{{last}}}}-L\\"
        rf"&\approx {tex(new_interest)}\\"
        rf"\text{{saved}}&\approx {tex(saved)}"
        r"\end{aligned}")

    rows = check_payoff(L, i, X_new, N, last, per)

    st.markdown("#### 📉 หนี้คงเหลือ: ผ่อนตามปกติ vs โปะเพิ่ม")
    old_rows = loan_by_recurrence(L, i, X, N0)
    old_name, new_name = f"ผ่อนตามปกติ ({N0} งวด)", f"โปะเพิ่ม ({N} งวด)"
    df = pd.concat([
        pd.DataFrame({"งวดที่": range(N0 + 1), "รายการ": old_name,
                      "หนี้คงเหลือ": [L] + [zero_if_tiny(r[2]) for r in old_rows]}),
        pd.DataFrame({"งวดที่": range(N + 1), "รายการ": new_name,
                      "หนี้คงเหลือ": [L] + [zero_if_tiny(r[2]) for r in rows]}),
    ])
    loan_compare_chart(df, unit)
    with st.expander("📋 ตารางผ่อนรายงวด (แบบโปะเพิ่ม)"):
        show_loan_table(rows, X_new, freq, last=last)


# 4.4 แสดงหน้าตามปุ่มที่เลือก
st.write("")
if st.session_state.mode == "deposit":
    tab_calc, tab_goal = st.tabs(["🌊  คำนวณเงินออม", "🎯  ตั้งเป้าหมาย"])
    with tab_calc:
        deposit_page()
    with tab_goal:
        goal_page()
else:
    tab_pay, tab_lgoal = st.tabs(["🔥  คำนวณค่างวด", "🎯  ตั้งเป้าหมาย"])
    with tab_pay:
        loan_page()
    with tab_lgoal:
        loan_goal_page()

st.markdown('<p class="footer" style="text-align:center;color:#5f8fa8;margin-top:2.5rem">'
            'AM200 · Recurrence Relation · 🐋</p>',
            unsafe_allow_html=True)
