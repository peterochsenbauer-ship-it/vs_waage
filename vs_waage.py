# vs_waage_dashboard.py
# Dashboard "Die Waage von VS" – 2 Tachos (0–100%), 3 Schieberegler, Zins-Bremse, Warnlogik
# Start: streamlit run vs_waage_dashboard.py

import streamlit as st
import plotly.graph_objects as go

# -----------------------------
# Konfiguration / Beschriftung
# -----------------------------
APP_TITLE = "Die Waage von VS – Bürger-Dashboard"

LABEL_V_ARROW = "Gewerbesteuer Villingen (Zufluss in den Pool)"
LABEL_S_ARROW = "Einnahmen S (Zufluss mit Mautstelle)"
LABEL_INTEREST = "Zins-Schleife (S → direkt in den Abfluss)"
LABEL_POOL = "Der VS-Pool (gemeinsamer Topf)"
LABEL_MOTOR = "Zentralverwaltung (Fixkosten) – Abfluss"
LABEL_RESET = "Realität wiederherstellen"

WARN_S_HEADER = "ℹ SELBSTREGULIERUNG: Schwenningen im Zins‑Stopp."
WARN_S_TEXT = (
    "Das System hat eine Sperre aktiviert. Schwenningen trägt die Last seiner Investitionen selbst; "
    "da das virtuelle Konto ins Minus läuft, tritt eine automatische Sperre für neue Projekte in Kraft, "
    "um den gemeinsamen VS‑Pool nicht zu belasten."
)

WARN_VS_HEADER = "⚡ VS‑ALARM: Verwaltungsmotor zu schwer für die Herzen."
WARN_VS_TEXT = (
    "Die kombinierten Budgets von Villingen und Schwenningen reichen nicht mehr aus, "
    "um den aktuellen Verwaltungsapparat zu finanzieren. Bitte nutzen Sie den mittleren Schieberegler, "
    "um die Effizienz zu steigern, bevor eine stadtweite Haushaltssperre eintritt."
)

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def make_gauge(value_0_100: float, title: str):
    """Plotly Gauge (0–100%)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value_0_100,
        number={"suffix": "%"},
        title={"text": title},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#333333"},
            "steps": [
                {"range": [0, 15], "color": "#d9534f"},   # rot
                {"range": [15, 40], "color": "#f0ad4e"}, # gelb/orange
                {"range": [40, 100], "color": "#5cb85c"} # grün
            ],
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": 15
            }
        }
    ))
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=260)
    return fig

def compute_model(v_tax_factor, s_invest_factor, motor_saving_factor,
                  v_base_rev, s_base_rev, interest_rate_s, motor_fixed_cost,
                  v_ref_for_100, s_ref_for_100):
    """
    Rechenmodell (entspricht der Backend-Logik):
    - Villingen Einnahmen wachsen mit V-Schieber
    - Schwenningen Einnahmen wachsen mit S-Schieber, aber Zinsen gehen direkt in den Abfluss
    - VS-Pool = V + S_netto
    - Motor = Fixkosten * (1 - Sparfaktor)
    - Motor wird proportional zur Beitragskraft zugeordnet (fair & erklärbar)
    - Tachos als Prozentwerte (0–100) gegenüber Referenz (100%-Anker)
    """
    # Einnahmen
    v_rev = v_base_rev * v_tax_factor
    s_rev_gross = s_base_rev * s_invest_factor
    s_interest = s_rev_gross * interest_rate_s
    s_rev_net = s_rev_gross - s_interest

    # Pool & Motor
    pool = v_rev + s_rev_net
    motor = motor_fixed_cost * (1.0 - motor_saving_factor)

    # Anteile (Schutz gegen Division durch 0)
    if pool > 0:
        v_motor_share = motor * (v_rev / pool)
        s_motor_share = motor * (s_rev_net / pool)
    else:
        v_motor_share = 0.0
        s_motor_share = 0.0

    # "Virtuelle Budgets" nach Motor
    v_budget = v_rev - v_motor_share
    s_budget = s_rev_net - s_motor_share

    # Tacho in Prozent (0–100) – 100% Referenz frei definierbar
    v_pct = clamp(100.0 * (v_budget / v_ref_for_100))
    s_pct = clamp(100.0 * (s_budget / s_ref_for_100))

    # Flags
    s_blocked = (s_budget < 0)
    vs_alarm = (v_budget < 0) and (s_budget < 0)

    return {
        "v_rev": v_rev,
        "s_rev_gross": s_rev_gross,
        "s_interest": s_interest,
        "s_rev_net": s_rev_net,
        "pool": pool,
        "motor": motor,
        "v_budget": v_budget,
        "s_budget": s_budget,
        "v_pct": v_pct,
        "s_pct": s_pct,
        "s_blocked": s_blocked,
        "vs_alarm": vs_alarm
    }

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# Session Defaults (Reset-fähig)
defaults = dict(
    v_tax_factor=1.00,         # 0.5–1.5
    s_invest_factor=1.00,      # 0.0–1.5
    motor_saving=0.00,         # 0.0–0.30 (0–30%)
    v_base_rev=100.0,
    s_base_rev=80.0,
    interest_rate=0.25,        # 25%
    motor_fixed=120.0,
    v_ref_for_100=100.0,       # 100%-Anker (kann z.B. V_Basis_Einnahmen sein)
    s_ref_for_100=80.0         # 100%-Anker (kann z.B. S_Basis_Einnahmen sein)
)

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Reset-Button
if st.button(LABEL_RESET):
    for k, v in defaults.items():
        st.session_state[k] = v

# Top: Parameter (optional sichtbar)
with st.expander("⚙️ Parameter (optional) – Basiswerte & Referenzen"):
    cA, cB, cC, cD = st.columns(4)
    with cA:
        st.session_state.v_base_rev = st.number_input("Basis-Einnahmen Villingen", min_value=0.0, value=float(st.session_state.v_base_rev), step=1.0)
        st.session_state.v_ref_for_100 = st.number_input("Referenz Villingen = 100%", min_value=1.0, value=float(st.session_state.v_ref_for_100), step=1.0)
    with cB:
        st.session_state.s_base_rev = st.number_input("Basis-Einnahmen Schwenningen", min_value=0.0, value=float(st.session_state.s_base_rev), step=1.0)
        st.session_state.s_ref_for_100 = st.number_input("Referenz Schwenningen = 100%", min_value=1.0, value=float(st.session_state.s_ref_for_100), step=1.0)
    with cC:
        st.session_state.interest_rate = st.slider("Zinsquote Schwenningen", 0.0, 0.60, float(st.session_state.interest_rate), 0.01)
    with cD:
        st.session_state.motor_fixed = st.number_input("Motor-Fixkosten (Zentralverwaltung)", min_value=0.0, value=float(st.session_state.motor_fixed), step=1.0)

st.divider()

# Hauptlayout: 3 Spalten (Villingen | Motor | Schwenningen)
left, mid, right = st.columns([1.1, 1.2, 1.1])

with left:
    st.subheader("LINKS: Fokus Villingen (V)")
    st.caption(LABEL_V_ARROW)
    st.session_state.v_tax_factor = st.slider("V‑Schieber (Steuerfaktor)", 0.50, 1.50, float(st.session_state.v_tax_factor), 0.01)

with mid:
    st.subheader("MITTE: Der Motor (Die Stadt VS)")
    st.caption(LABEL_POOL + " + " + LABEL_MOTOR)
    st.session_state.motor_saving = st.slider("Motor‑Schieber (Spar‑Potential)", 0.00, 0.30, float(st.session_state.motor_saving), 0.01)

with right:
    st.subheader("RECHTS: Fokus Schwenningen (S)")
    st.caption(LABEL_S_ARROW)
    st.session_state.s_invest_factor = st.slider("S‑Schieber (Investitionsfaktor)", 0.00, 1.50, float(st.session_state.s_invest_factor), 0.01)

# Berechnung
m = compute_model(
    st.session_state.v_tax_factor,
    st.session_state.s_invest_factor,
    st.session_state.motor_saving,
    st.session_state.v_base_rev,
    st.session_state.s_base_rev,
    st.session_state.interest_rate,
    st.session_state.motor_fixed,
    st.session_state.v_ref_for_100,
    st.session_state.s_ref_for_100
)

# Visualisierung: Pfeilstärken als Balken (einfach, aber sehr verständlich)
# (Excel-Pfeil-Dicken-Effekt wird hier als "Stärke" dargestellt)
with left:
    st.plotly_chart(make_gauge(m["v_pct"], "Tacho Villingen – Virtuelles Budget"), use_container_width=True)
    st.markdown("**Pfeilstärke (Zufluss V → Pool)**")
    st.progress(clamp((st.session_state.v_tax_factor - 0.50) / (1.50 - 0.50) * 100) / 100)
    st.caption(f"Einnahmen V: {m['v_rev']:.1f} | Budget V nach Motor: {m['v_budget']:.1f}")

with mid:
    st.markdown("### " + LABEL_POOL)
    st.metric("VS‑Pool (netto)", f"{m['pool']:.1f}")
    st.markdown("### " + LABEL_MOTOR)
    st.metric("Motor (effektiv)", f"{m['motor']:.1f}")

    st.markdown("**Abflussstärke (Motor ↓)**")
    # Je mehr gespart wird, desto kleiner der Abfluss → invers als progress
    st.progress(clamp((1.0 - st.session_state.motor_saving / 0.30) * 100) / 100)

    # „Saug-Wirkung“: Wenn Motor spart, "leuchten" beide Tachos (hier: Hinweisbanner)
    if st.session_state.motor_saving > 0:
        st.info("Saug‑Wirkung aktiv: Weniger Motor‑Abfluss wirkt auf beide Seiten (Tachos reagieren).")

with right:
    st.plotly_chart(make_gauge(m["s_pct"], "Tacho Schwenningen – Virtuelles Budget"), use_container_width=True)
    st.markdown("**Zins‑Schleife (S → Abfluss)**")
    # Zinslast sichtbar machen (0..100 normiert)
    interest_norm = 0 if m["s_rev_gross"] <= 0 else clamp(m["s_interest"] / max(1e-9, m["s_rev_gross"]) * 100)
    st.progress(interest_norm / 100)
    st.caption(f"Einnahmen S brutto: {m['s_rev_gross']:.1f} | Zinsen: {m['s_interest']:.1f} | Budget S nach Motor: {m['s_budget']:.1f}")

# Warnmeldungen
st.divider()

if m["s_blocked"]:
    st.warning(f"**{WARN_S_HEADER}**\n\n{WARN_S_TEXT}")

if m["vs_alarm"]:
    st.error(f"**{WARN_VS_HEADER}**\n\n{WARN_VS_TEXT}")

# Footer: Transparenzbox (psychologisch wichtig!)
with st.expander("🔍 Transparenz: Was das System gerade rechnet"):
    st.write({
        "V_Steuer_Faktor": st.session_state.v_tax_factor,
        "S_Invest_Faktor": st.session_state.s_invest_factor,
        "Motor_Spar_Faktor": st.session_state.motor_saving,
        "V_Einnahmen": m["v_rev"],
        "S_Einnahmen_brutto": m["s_rev_gross"],
        "S_Zinslast": m["s_interest"],
        "S_Einnahmen_netto": m["s_rev_net"],
        "VS_Pool": m["pool"],
        "Motor_effektiv": m["motor"],
        "V_Budget_nach_Motor": m["v_budget"],
        "S_Budget_nach_Motor": m["s_budget"],
        "V_Tacho_%": m["v_pct"],
        "S_Tacho_%": m["s_pct"],
    })