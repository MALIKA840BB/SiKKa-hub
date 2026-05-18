import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from collections import deque
import random
import io

# =====================================================
# CONFIG & STYLE
# =====================================================
st.set_page_config(page_title="Sikka Hub - Intelligence Hub", layout="wide")
st.markdown("""
<style>
.stMetric { background: white; padding: 15px; border-radius: 12px; box-shadow: 0px 2px 8px rgba(0,0,0,0.08); }
.alert-green { background-color: #e8f5e9; padding: 10px; border-left: 5px solid green; border-radius: 8px; margin-bottom: 10px; }
.alert-orange { background-color: #fff3e0; padding: 10px; border-left: 5px solid orange; border-radius: 8px; margin-bottom: 10px; }
.alert-red { background-color: #ffebee; padding: 10px; border-left: 5px solid red; border-radius: 8px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONSTANTES & CLASSES
# =====================================================
PROVINCES = ["Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", "Agadir", "Oujda", "Meknès", "Kénitra", "Tétouan", "Extérieur"]
EQUIPE = ["Ahmed", "Anouar", "Chaimae", "Romayssae", "Malika", "Hamza", "Mohammed", "Brahim", "Afnane", "Titrite"]

class Passport:
    def __init__(self, pid, category, arrival_day, province, is_urgent=False):
        self.pid = pid
        self.category = category 
        self.province = province
        self.arrival_day = arrival_day
        self.is_urgent = is_urgent

# =====================================================
# SIMULATION ENGINE
# =====================================================
def run_simulation(backlog_init, sim_days, ot_active, inflow_int, inflow_ext, min_agents, max_agents, min_cap, max_cap, pannes_actives):
    
    error_rate = 0.05
    panne_prob = 0.05
    q_vip = {prov: deque() for prov in PROVINCES}
    q_urgent = {prov: deque() for prov in PROVINCES}
    q_nouv = {prov: deque() for prov in PROVINCES}
    q_backlog = {prov: deque() for prov in PROVINCES}

    for i in range(backlog_init):
        prov = random.choice(PROVINCES)
        q_backlog[prov].append(Passport(f"OLD_{i}", "Ordinaire", -5, prov))

    history = []
    lot_sizes = []
    delays = []
    p_id_counter = 0
    agent_stats = {nom: {"Jours_Présent": 0, "Production_Totale": 0} for nom in EQUIPE}

    for day in range(sim_days):
        actual_max_agents = min(max_agents, len(EQUIPE))
        actual_min_agents = min(min_agents, actual_max_agents)
        nb_presents = random.randint(actual_min_agents, actual_max_agents)
        present_agents = random.sample(EQUIPE, nb_presents)

        base_cap = sum(random.randint(min_cap, max_cap) for _ in range(nb_presents))
        daily_cap = int(base_cap * 1.25) if ot_active else base_cap

        if pannes_actives and random.random() < panne_prob:
            daily_cap = int(daily_cap * 0.5)

        quota_nouveaux = int(daily_cap * 0.80)
        quota_backlog = int(daily_cap * 0.20)

        for _ in range(inflow_int):
            prov = random.choice(PROVINCES[:-1]) 
            rand = random.random()
            if rand < 0.10: q_vip[prov].append(Passport(f"P_{p_id_counter}", "VIP", day, prov))
            elif rand < 0.15: q_urgent[prov].append(Passport(f"P_{p_id_counter}", "Ordinaire", day, prov, is_urgent=True))
            else: q_nouv[prov].append(Passport(f"P_{p_id_counter}", "Ordinaire", day, prov))
            p_id_counter += 1

        for _ in range(inflow_ext):
            rand = random.random()
            if rand < 0.10: q_vip["Extérieur"].append(Passport(f"P_{p_id_counter}", "VIP", day, "Extérieur"))
            elif rand < 0.15: q_urgent["Extérieur"].append(Passport(f"P_{p_id_counter}", "Ordinaire", day, "Extérieur", is_urgent=True))
            else: q_nouv["Extérieur"].append(Passport(f"P_{p_id_counter}", "Ordinaire", day, "Extérieur"))
            p_id_counter += 1

        d_out = 0; d_vip = 0; d_nouv = 0; d_anc = 0; forced_closures = 0

        while d_out < daily_cap:
            action_taken = False
            current_target = 60 if (len(lot_sizes) % 2 == 0) else 20
            
            for prov in PROVINCES:
                limit = min(current_target, 100 if prov == "Extérieur" else 60)
                for q in [q_vip[prov], q_urgent[prov]]:
                    if q and d_out < daily_cap:
                        c = 0
                        while q and c < limit and d_out < daily_cap:
                            p = q.popleft()
                            delays.append(day - p.arrival_day)
                            d_out += 1; d_vip += 1; c += 1
                        if c > 0: lot_sizes.append(c); action_taken = True

            for prov in PROVINCES:
                if q_nouv[prov] and (day - q_nouv[prov][0].arrival_day) >= 2 and d_out < daily_cap:
                    c = 0
                    while q_nouv[prov] and c < current_target Glen d_out < daily_cap:
                        p = q_nouv[prov].popleft()
                        delays.append(day - p.arrival_day)
                        d_out += 1; d_nouv += 1; c += 1
                    if c > 0: lot_sizes.append(c); forced_closures += 1; action_taken = True

            for prov in PROVINCES:
                if len(q_nouv[prov]) >= current_target and d_out + current_target <= daily_cap:
                    for _ in range(current_target):
                        p = q_nouv[prov].popleft()
                        delays.append(day - p.arrival_day)
                        d_out += 1; d_nouv += 1
                    lot_sizes.append(current_target); action_taken = True

            for prov in PROVINCES:
                if len(q_backlog[prov]) >= current_target and d_out + current_target <= daily_cap:
                    for _ in range(current_target):
                        p = q_backlog[prov].popleft()
                        delays.append(day - p.arrival_day)
                        d_out += 1; d_anc += 1
                    lot_sizes.append(current_target); action_taken = True

            if not action_taken: break

        if d_out > 0 and nb_presents > 0:
            prod = d_out // nb_presents
            for idx, name in enumerate(present_agents):
                agent_stats[name]["Jours_Présent"] += 1
                agent_stats[name]["Production_Totale"] += prod + (1 if idx < (d_out % nb_presents) else 0)

        prov_backlog = {p: len(q_backlog[p]) + len(q_nouv[p]) + len(q_vip[p]) + len(q_urgent[p]) for p in PROVINCES}
        total_backlog = sum(prov_backlog.values())

        # هنا رجّعنا كاع السطور بالتفصيل الممل للـ Excel والواجهة بجوج
        history.append({
            "Jour": day + 1,
            "Staff_Présent": nb_presents,
            "Capacité_Jour": daily_cap,
            "Clôtures_Forcées": forced_closures,
            "VIP_Urgent_Traités": d_vip,
            "Nouveaux_Traités": d_nouv,
            "Anciens_Backlog_Traités": d_anc,
            "Output_Total": d_out,
            "Backlog_Restant_Total": total_backlog,
            "Moyenne_Lot": np.mean(lot_sizes) if lot_sizes else 0,
            "DMT_Moyen_Jour (Jours)": np.mean(delays[-d_out:]) if d_out > 0 else 0,
            **{f"Backlog_{p}": v for p, v in prov_backlog.items()}
        })

    return history, lot_sizes, agent_stats, prov_backlog, delays, sim_days

# =====================================================
# UI
# =====================================================
st.title("🚀 Sikka Intelligence Hub v2")
st.subheader("Smart Production & Aide à la Décision Logistique")

if 'sim_done' not in st.session_state: st.session_state.sim_done = False

with st.sidebar:
    st.header("⚙️ Paramètres")
    inflow_int = st.number_input("MI (Intérieur)", value=4500, step=100)
    inflow_ext = st.number_input("MAEC (Extérieur)", value=3000, step=100)
    st.markdown("---")
    st.header("🎯 Objectifs (Targets)")
    target_lot = st.slider("Cible Moyenne Lot", 30, 60, 40)
    target_dmt = st.number_input("Cible Délai (Jours)", value=1.5, step=0.1)
    st.markdown("---")
    b_init = st.number_input("Backlog Initial", value=30000, step=5000)
    days = st.slider("Simulation (Jours)", 7, 60, 30)
    ot = st.checkbox("Heures Supp (+25%)", value=True)
    pannes = st.checkbox("Risques Pannes", value=True)

if st.button("🚀 Lancer l'Analyse Intelligente"):
    hist, lots, agent_stats, last_prov, all_delays, total_sim_days = run_simulation(b_init, days, ot, inflow_int, inflow_ext, 7, 10, 800, 1200, pannes)
    st.session_state.df = pd.DataFrame(hist)
    st.session_state.lots = lots
    st.session_state.agent_stats = agent_stats
    st.session_state.last_prov = last_prov
    st.session_state.avg_dmt = np.mean(all_delays)
    st.session_state.total_sim_days = total_sim_days
    st.session_state.sim_done = True

if st.session_state.sim_done:
    df = st.session_state.df
    avg_lot = np.mean(st.session_state.lots)
    
    # ROW 1: KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🎯 Moyenne Lot", f"{avg_lot:.1f}", f"{avg_lot - target_lot:.1f} vs Target")
    c2.metric("⏱️ Délai Moyen (DMT)", f"{st.session_state.avg_dmt:.2f} j", f"{st.session_state.avg_dmt - target_dmt:.2f} vs Target", delta_color="inverse")
    c3.metric("📦 Backlog Final", f"{df['Backlog_Restant_Total'].iloc[-1]:,}")
    c4.metric("📈 Production Totale", f"{df['Output_Total'].sum():,}")

    st.markdown("### 🧠 Analyse Decisionnelle")
    if avg_lot < target_lot:
        st.markdown(f'<div class="alert-orange">⚠️ <strong>Alerte Optimisation :</strong> La taille des lots ({avg_lot:.1f}) est inférieure à l\'objectif ({target_lot}).</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-green">✅ <strong>Performance Lot :</strong> L\'objectif de regroupement est atteint.</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.subheader("📊 Flux de Production Quotidien")
        fig = px.area(df, x="Jour", y="Output_Total", title="Évolution de la capacité de sortie")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📍 Backlog par Province")
        prov_data = pd.DataFrame(list(st.session_state.last_prov.items()), columns=['Province', 'Reste'])
        fig_pie = px.pie(prov_data, values='Reste', names='Province', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("👥 Performance de l'Équipe")
    df_ag = pd.DataFrame.from_dict(st.session_state.agent_stats, orient='index').reset_index().rename(columns={'index': 'Agent'})
    df_ag['Jours Présents'] = df_ag['Jours_Présent']
    df_ag['Jours Absents'] = st.session_state.total_sim_days - df_ag['Jours Présents']
    df_ag['Production Totale'] = df_ag['Production_Totale']

    fig_ag = px.bar(df_ag, x='Agent', y='Production Totale', color='Production Totale', text_auto=True)
    st.plotly_chart(fig_ag, use_container_width=True)

    st.markdown("---")
    st.subheader("🔎 Analyse Détaillée par Agent")
    agent_choisi = st.selectbox("Sélectionnez un membre de l'équipe :", df_ag['Agent'])
    stats_agent = df_ag[df_ag['Agent'] == agent_choisi].iloc[0]
    st.info(f"👤 **{agent_choisi}** : Présent(e) pendant **{stats_agent['Jours Présents']} jours** | Absent(e) pendant **{stats_agent['Jours Absents']} jours** | Production de **{stats_agent['Production Totale']:,}**.")

    with st.expander("📋 Voir les détails d'exécution (Tableau Complet نهار بنهار)"):
        st.dataframe(df, use_container_width=True)

    # =====================================================
    # EXPORT EXCEL ULTRA DETAILLÉ (هنا فين رجع حسن بزاااف)
    # =====================================================
    st.markdown("---")
    st.subheader("📥 Exporter les Résultats")
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # الصفحة 1 فيها كاع التفاصيل المملة اليومية كيف كان ف الكود القديم وزيادة
        df.to_excel(writer, sheet_name='Suivi_Quotidien_Complet', index=False)
        # الصفحة 2 فيها تفاصيل الموظفين والغياب والحضور
        df_ag[['Agent', 'Jours Présents', 'Jours Absents', 'Production Totale']].to_excel(writer, sheet_name='Performance_Personnel', index=False)
        # الصفحة 3 فيها توزيع المدن
        prov_data.to_excel(writer, sheet_name='Backlog_Par_Province', index=False)
        
        # موازنة حجم الخانات تلقائياً باش يبان التقرير نقي ومقاد للشاف
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)
    
    st.download_button(
        label="📥 Télécharger le Rapport Excel Complet (Version Pro)", 
        data=buffer.getvalue(), 
        file_name='Sikka_Intelligence_Report_v2.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
