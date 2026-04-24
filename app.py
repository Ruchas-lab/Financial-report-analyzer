import streamlit as st

st.set_page_config(page_title="Financial Ratio Calculator", layout="centered")

st.title("Financial Ratio Calculator")
st.subheader("Built for consulting, investment, and corporate finance analysis")
st.markdown("---")

with st.form("inputs"):
    company_name = st.text_input("Company Name", placeholder="e.g. Apple Inc.")
    st.markdown("##### Financial Figures")
    col1, col2 = st.columns(2)
    with col1:
        revenue = st.number_input("Total Revenue", min_value=0.0, step=1000.0, format="%.2f")
        gross_profit = st.number_input("Gross Profit", min_value=0.0, step=1000.0, format="%.2f")
        net_income = st.number_input("Net Income", step=1000.0, format="%.2f")
        total_equity = st.number_input("Total Shareholders Equity", step=1000.0, format="%.2f")
    with col2:
        total_debt = st.number_input("Total Debt", min_value=0.0, step=1000.0, format="%.2f")
        current_assets = st.number_input("Current Assets", min_value=0.0, step=1000.0, format="%.2f")
        current_liabilities = st.number_input("Current Liabilities", min_value=0.0, step=1000.0, format="%.2f")

    submitted = st.form_submit_button("Calculate Ratios", use_container_width=True)

def badge(color, label):
    colors = {"green": "#1e7e34", "amber": "#d39e00", "red": "#bd2130"}
    hex_color = colors.get(color, "#555")
    return f'<span style="background:{hex_color};color:white;padding:3px 10px;border-radius:4px;font-size:0.8rem;font-weight:600">{label}</span>'

def ratio_card(name, value, fmt, interpretation, color, benchmark_note):
    color_map = {"green": "#d4edda", "amber": "#fff3cd", "red": "#f8d7da"}
    border_map = {"green": "#28a745", "amber": "#ffc107", "red": "#dc3545"}
    bg = color_map.get(color, "#f8f9fa")
    border = border_map.get(color, "#ccc")
    st.markdown(
        f"""
        <div style="border-left:5px solid {border};background:{bg};padding:14px 18px;
                    border-radius:6px;margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <strong style="font-size:1rem">{name}</strong>
                {badge(color, interpretation)}
            </div>
            <div style="font-size:1.6rem;font-weight:700;margin:6px 0">{fmt}</div>
            <div style="font-size:0.82rem;color:#555">{benchmark_note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if submitted:
    errors = []
    if revenue == 0:
        errors.append("Total Revenue cannot be zero.")
    if current_liabilities == 0:
        errors.append("Current Liabilities cannot be zero.")

    if errors:
        for e in errors:
            st.error(e)
    else:
        st.markdown("---")
        heading = f"### Results for {company_name}" if company_name else "### Results"
        st.markdown(heading)
        st.markdown(" ")

        # 1. Gross Profit Margin
        gpm = (gross_profit / revenue) * 100
        if gpm >= 40:
            gpm_color, gpm_interp = "green", "Strong"
        elif gpm >= 20:
            gpm_color, gpm_interp = "amber", "Moderate"
        else:
            gpm_color, gpm_interp = "red", "Weak"
        ratio_card(
            "Gross Profit Margin",
            gpm,
            f"{gpm:.1f}%",
            gpm_interp,
            gpm_color,
            "Benchmark: ≥40% strong | 20–40% moderate | <20% weak — varies significantly by industry",
        )

        # 2. Net Profit Margin
        npm = (net_income / revenue) * 100
        if npm >= 15:
            npm_color, npm_interp = "green", "Strong"
        elif npm >= 5:
            npm_color, npm_interp = "amber", "Moderate"
        else:
            npm_color, npm_interp = "red", "Weak"
        ratio_card(
            "Net Profit Margin",
            npm,
            f"{npm:.1f}%",
            npm_interp,
            npm_color,
            "Benchmark: ≥15% strong | 5–15% moderate | <5% or negative is a concern",
        )

        # 3. Return on Equity (ROE)
        if total_equity == 0:
            st.warning("ROE skipped — Shareholders Equity is zero.")
        else:
            roe = (net_income / total_equity) * 100
            if roe >= 15:
                roe_color, roe_interp = "green", "Strong"
            elif roe >= 8:
                roe_color, roe_interp = "amber", "Moderate"
            else:
                roe_color, roe_interp = "red", "Weak"
            ratio_card(
                "Return on Equity (ROE)",
                roe,
                f"{roe:.1f}%",
                roe_interp,
                roe_color,
                "Benchmark: ≥15% strong | 8–15% moderate | <8% suggests poor capital efficiency",
            )

        # 4. Debt-to-Equity Ratio
        if total_equity == 0:
            st.warning("D/E Ratio skipped — Shareholders Equity is zero.")
        else:
            de = total_debt / total_equity
            if de <= 1.0:
                de_color, de_interp = "green", "Low Risk"
            elif de <= 2.0:
                de_color, de_interp = "amber", "Moderate Risk"
            else:
                de_color, de_interp = "red", "High Risk"
            ratio_card(
                "Debt-to-Equity Ratio",
                de,
                f"{de:.2f}x",
                de_interp,
                de_color,
                "Benchmark: ≤1.0x low risk | 1–2x moderate | >2x high leverage — context matters by sector",
            )

        # 5. Current Ratio
        cr = current_assets / current_liabilities
        if cr >= 2.0:
            cr_color, cr_interp = "green", "Healthy"
        elif cr >= 1.0:
            cr_color, cr_interp = "amber", "Adequate"
        else:
            cr_color, cr_interp = "red", "At Risk"
        ratio_card(
            "Current Ratio",
            cr,
            f"{cr:.2f}x",
            cr_interp,
            cr_color,
            "Benchmark: ≥2.0x healthy | 1–2x adequate | <1.0x signals potential liquidity issues",
        )

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#888;font-size:0.8rem'>"
    "Built by Ruchas &nbsp;|&nbsp; Financial Report Analyzer v0.1 &nbsp;|&nbsp; "
    "<a href='https://github.com/Ruchas-lab' style='color:#888'>github.com/Ruchas-lab</a>"
    "</div>",
    unsafe_allow_html=True,
)
