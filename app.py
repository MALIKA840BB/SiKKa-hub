import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from collections import deque
import random
import io  # زدت هادي باش نتحكمو ف تنزيل الـ Excel

# =====================================================
# CONFIG & STYLE
# =====================================================
st.set_page_config(page_title="Sikka Hub - Smart Production", layout="wide")
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
PROVINCES = [
    "Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", 
    "Agadir", "Oujda", "Meknès", "Kénitra", "Tétouan", "Extérieur"
]

EQUIPE = [
    "Ahmed", "Anouar", "Chaimae", "Romayssae", "Malika", 
    "Hamza", "Mohammed", "Brahim", "Afnane", "Titrite"
]

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
        q_backlog[prov].append(Passport(f"OLD_{i}", "Ordinaire", -10, prov))

    history = []
    lot_sizes = []
    p_id_counter = 0

    agent_stats = {nom: {"Jours_Présent": 0, "Production_Totale": 0} for nom in EQUIPE}

    for day in range(sim_days):
        
        actual_max_agents = min(max_agents, len(EQUIPE))
        actual_min_agents = min(min_agents, actual_max_agents)
        
        nb_presents = random.randint(actual_min_agents, actual_max_agents)
        present_agents = random.sample(EQUIPE, nb_presents)

        base_cap = sum(random.randint(min_cap, max_cap) for _ in range(nb_presents))
        daily_cap = int(base_cap * 1.25) if ot_active else base_cap

        panne_jour = False
        if pannes_actives and random.random() < panne_prob:
            panne_jour = True
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
                max_prov = 100 if prov == "Extérieur" else 60
                lot_limit = min(current_target, max_prov) 
                if q_vip[prov] and d_out < daily_cap:
                    lot_count = 0
                    while q_vip[prov] and lot_count < lot_limit and d_out < daily_cap:
                        q_vip[prov].popleft()
                        d_out += 1; d_vip += 1; lot_count += 1
                    if lot_count > 0:
                        lot_sizes.append(lot_count)
                        action_taken = True
                    current_target = 60 if (len(lot_sizes) % 2 == 0) else 20

            for prov in PROVINCES:
                max_prov = 100 if prov == "Extérieur" else 60
                lot_limit = min(current_target, max_prov)
                if q_urgent[prov] and d_out < daily_cap:
                    lot_count = 0
                    while q_urgent[prov] and lot_count < lot_limit and d_out < daily_cap:
                        q_urgent[prov].popleft()
                        d_out += 1; d_vip += 1; lot_count += 1
                    if lot_count > 0:
                        lot_sizes.append(lot_count)
                        action_taken = True
                    current_target = 60 if (len(lot_sizes) % 2 == 0) else 20

            for prov in PROVINCES:
                max_prov = 100 if prov == "Extérieur" else 60
                lot_limit = min(current_target, max_prov)
                if q_nouv[prov] and (day - q_nouv[prov][0].arrival_day) >= 2 and d_out < daily_cap:
                    lot_count = 0
                    while q_nouv[prov] and lot_count < lot_limit and d_out < daily_cap:
                        p = q_nouv[prov].popleft()
                        if random.random() < error_rate:
                            q_nouv[prov].append(p)
                            d_out += 1
                        else:
                            d_out += 1; d_nouv += 1; lot_count += 1
                    if lot_count > 0:
                        lot_sizes.append(lot_count)
                        forced_closures += 1
                        action_taken = True
                    current_target = 60 if (len(lot_sizes) % 2 == 0) else 20

            for prov in PROVINCES:
                max_prov = 100 if prov == "Extérieur" else 60
                lot_limit = min(current_target, max_prov)
                if len(q_nouv[prov]) >= lot_limit and d_out + lot_limit <= daily_cap and d_nouv + lot_limit <= quota_nouveaux:
                    lot_count = 0
                    for _ in range(lot_limit):
                        p = q_nouv[prov].popleft()
                        if random.random() < error_rate:
                            q_nouv[prov].append(p)
                            d_out += 1
                        else:
                            d_out += 1; d_nouv += 1; lot_count += 1
                    if lot_count > 0:
                        lot_sizes.append(lot_count)
                        action_taken = True
                    current_target = 60 if (len(lot_sizes) % 2 == 0) else 20

            for prov in PROVINCES:
                max_prov = 100 if prov == "Extérieur" else 60
                lot_limit = min(current_target, max_prov)
                if len(q_backlog[prov]) >= lot_limit and d_out + lot_limit <= daily_cap and d_anc + lot_limit <= quota_backlog:
                    lot_count = 0
                    for _ in range(lot_limit):
                        p = q_backlog[prov].popleft()
                        if random.random() < error_rate:
                            q_backlog[prov].append(p)
                            d_out += 1
                        else:
                            d_out += 1; d_anc += 1; lot_count += 1
                    if lot_count > 0:
                        lot_sizes.append(lot_count)
                        action_taken = True
                    current_target = 60 if (len(lot_sizes) % 2 == 0) else 20

            if not action_taken:
                break

        if d_out > 0 and nb_presents > 0:
            prod_per_agent = d_out // nb_presents
            remainder = d_out % nb_presents
            for idx, agent_name in enumerate(present_agents):
                agent_stats[agent_name]["Jours_Présent"] += 1
                agent_stats[agent_name]["Production_Totale"] += prod_per_agent + (1 if idx < remainder else 0)

        backlog_total = sum(len(q_backlog[p]) + len(q_nouv[p]) + len(q_vip[p]) + len(q_urgent[p]) for p in PROVINCES)

        history.append({
            "Jour": day + 1,
            "Staff_Présent": nb_presents,
            "Capacité_Jour": daily_cap,
            "Clôtures_Forcées": forced_closures,
            "VIP_Urgent": d_vip,
            "Nouveaux_Traités": d_nouv,
            "Anciens_Backlog": d_anc,
            "Output_Total": d_out,
            "Backlog_Restant": backlog_total,
            "Moyenne_Lot": np.mean(lot_sizes) if lot_sizes else 0
        })

    return history, lot_sizes, agent_stats

# =====================================================
# INTERFACE STREAMLIT
# =====================================================
st.title("🚀 Sikka Intelligence Hub")
st.subheader("Smart Logistique : Suivi de la Productivité de l'Équipe")

if 'sim_done' not in st.session_state:
    st.session_state.sim_done = False

with st.sidebar:
    st.header("⚙️ Flux Entrant")
    inflow_int = st.number_input("MI (Intérieur)", value=4500, step=100)
    inflow_ext = st.number_input("MAEC (Extérieur)", value=3000, step=100)
    
    st.markdown("---")
    st.header("👥 Paramètres d'Équipe")
    col1, col2 = st.columns(2)
    min_agents = col1.number_input("Staff Min", value=7, min_value=1, max_value=10)
    max_agents = col2.number_input("Staff Max", value=10, min_value=1, max_value=10)
    
    col3, col4 = st.columns(2)
    min_cap = col3.number_input("Prod. Min/Agent", value=800, step=50)
    max_cap = col4.number_input("Prod. Max/Agent", value=1200, step=50)
    
    ot = st.checkbox("Activer Heures Supplémentaires (+25%)", value=True)
    pannes = st.checkbox("⚠️ Risques de Pannes (5%)", value=True)
    
    st.markdown("---")
    st.header("📦 Paramètres Globaux")
    b_init = st.number_input("Backlog Initial", value=30000, step=1000)
    days = st.slider("Jours de Simulation", 7, 60, 30)

if st.button("🚀 Lancer l'Optimisation"):
    hist, lots, agent_stats = run_simulation(b_init, days, ot, inflow_int, inflow_ext, min_agents, max_agents, min_cap, max_cap, pannes)
    st.session_state.df = pd.DataFrame(hist)
    st.session_state.lots = lots
    st.session_state.agent_stats = agent_stats
    st.session_state.sim_done = True

if st.session_state.sim_done:
    df = st.session_state.df
    lots = st.session_state.lots
    agent_stats = st.session_state.agent_stats

    st.subheader("📈 KPIs Globaux")
    c1, c2, c3, c4 = st.columns(4)
    avg_lot = np.mean(lots) if lots else 0
    c1.metric("🎯 Moyenne Lot", f"{avg_lot:.1f}", "✅ Cible atteinte" if 35 <= avg_lot <= 45 else "❌ Impact des urgences")
    c2.metric("📦 Backlog Final", f"{df['Backlog_Restant'].iloc[-1]:,}")
    c3.metric("🚨 Clôtures Forcées", f"{df['Clôtures_Forcées'].mean():.1f}/jr", "Lots < 40 sauvés")
    c4.metric("⚡ Capacité Moyenne", f"{df['Capacité_Jour'].mean():.0f}/jr")

    st.markdown("---")
    if df['Backlog_Restant'].iloc[-1] > b_init:
        st.markdown('<div class="alert-red">⚠️ <strong>Alerte :</strong> Le Backlog est en train d\'augmenter ! La capacité actuelle est insuffisante pour absorber le flux.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-green">✅ <strong>Situation Maîtrisée :</strong> L\'équipe arrive à réduire le Backlog de manière efficace.</div>', unsafe_allow_html=True)

    st.subheader("📊 Évolution de la Production Quotidienne")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['Jour'], y=df['Nouveaux_Traités'], name="Nouveaux", marker_color='#34a853'))
    fig.add_trace(go.Bar(x=df['Jour'], y=df['Anciens_Backlog'], name="Backlog", marker_color='#1a73e8'))
    fig.add_trace(go.Bar(x=df['Jour'], y=df['VIP_Urgent'], name="VIP/Urgent", marker_color='#fbbc04'))
    fig.update_layout(barmode='stack', template="plotly_white", height=450)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("👥 Productivité Cumulée par Agent")
    df_agents = pd.DataFrame.from_dict(agent_stats, orient='index').reset_index()
    df_agents.columns = ['Agent', 'Jours Présents', 'Production Totale']
    df_agents = df_agents.sort_values(by='Production Totale', ascending=False)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_agents['Agent'], 
        y=df_agents['Production Totale'],
        text=df_agents['Production Totale'], 
        textposition='auto',
        marker_color='#9c27b0', 
        name="Production"
    ))
    fig2.update_layout(template="plotly_white", height=400, xaxis_title="Membres de l'équipe", yaxis_title="Total des passeports traités")
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("🔎 Analyse Détaillée par Agent")
    agent_choisi = st.selectbox("Sélectionnez un membre de l'équipe :", df_agents['Agent'])
    stats_agent = df_agents[df_agents['Agent'] == agent_choisi].iloc[0]
    st.info(f"**{agent_choisi}** a été présent(e) pendant **{stats_agent['Jours Présents']} jours** et a traité un total de **{stats_agent['Production Totale']} passeports**.")

    with st.expander("📋 Voir les détails d'exécution (Tableau)"):
        st.dataframe(df, use_container_width=True)
        
    with st.expander("👤 Voir les détails de présence des agents"):
        st.dataframe(df_agents, use_container_width=True)

    # =====================================================
    #  MODIFICATION ICI : EXPORT EXCEL PRO SANS ERREUR
    # =====================================================
    st.markdown("---")
    st.subheader("📥 Exporter les Résultats")
    
    # تحضير ملف إكسيل حقيقي منظم في الذاكرة
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # الورقة الأولى: نتائج المحاكاة اليومية
        df.to_excel(writer, sheet_name='Suivi_Quotidien', index=False)
        # الورقة الثانية: إنتاجية الفريق
        df_agents.to_excel(writer, sheet_name='Productivite_Agents', index=False)
        
        # تعديل قياس الخانات تلقائياً باش مايبقاش النص مخبي
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = col[0].column_letter
                worksheet.column_dimensions[col_letter].width = max(max_len + 3, 12)

    # زر التحميل بصيغة Excel حقيقية (.xlsx)
    st.download_button(
        label="📊 Télécharger le Rapport Complet (Excel)",
        data=buffer.getvalue(),
        file_name='Rapport_Simulation_Sikka.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
