import streamlit as st
import pandas as pd
import random
import json
import gspread

st.set_page_config(page_title="Hivatalos FIFA 2026 VB Dashboard", layout="wide")

# --- FEJLÉC ÉS MENÜ ELTÜNTETÉSE A LÁTOGATÓK ELŐL ---
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            .stDeployButton {visibility: hidden;}
            [data-testid="stToolbar"] {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- ADMIN VÉDELEM BEÁLLÍTÁSA TITKOS JELSZÓVAL ---
admin_password = st.sidebar.text_input("🔒 Admin jelszó:", type="password")

# Itt már a Streamlit védett "Secrets" menüjéből olvassa ki a jelszót!
# Ha valamiért nincs beállítva a secrets, alapértelmezetten egy nagyon bonyolult jelszót kér.
helyes_jelszo = st.secrets.get("admin_pass", "VeszhelyzetiJelszo999!!!")

is_admin = (admin_password == helyes_jelszo)

if not is_admin:
    st.sidebar.info("Csak olvasási mód. A meccsek szerkesztéséhez add meg az admin jelszót!")
else:
    st.sidebar.success("✅ Admin mód aktív: Szerkesztés engedélyezve!")

# --- HIVATALOS 2026-OS VB CSOPORTOK ---
GROUPS = {
    "A csoport": ["Mexikó", "Dél-Afrika", "Dél-Korea", "Csehország"],
    "B csoport": ["Kanada", "Bosznia-Hercegovina", "Katar", "Svájc"],
    "C csoport": ["Brazília", "Marokkó", "Haiti", "Skócia"],
    "D csoport": ["Egyesült Államok", "Paraguay", "Ausztrália", "Törökország"],
    "E csoport": ["Németország", "Curaçao", "Elefántcsontpart", "Ecuador"],
    "F csoport": ["Hollandia", "Japán", "Svédország", "Tunézia"],
    "G csoport": ["Belgium", "Egyiptom", "Irán", "Új-Zéland"],
    "H csoport": ["Spanyolország", "Zöld-foki Köztársaság", "Szaúd-Arábia", "Uruguay"],
    "I csoport": ["Franciaország", "Szenegál", "Irak", "Norvégia"],
    "J csoport": ["Argentína", "Algéria", "Ausztria", "Jordánia"],
    "K csoport": ["Portugália", "Kongói DK", "Üzbegisztán", "Kolumbia"],
    "L csoport": ["Anglia", "Horvátország", "Ghána", "Panama"]
}

all_teams_list = []
for g_teams in GROUPS.values():
    all_teams_list.extend(g_teams)

# --- ALAPÉRTELMEZETT STRUKTÚRA ÜRES ADATOK ESETÉRE ---
DEFAULT_DATA = {
    "matches": [],
    "ko_state": {
        'generated': False,
        'R32': [{'home': None, 'away': None, 'winner': None} for _ in range(16)],
        'R16': [{'home': None, 'away': None, 'winner': None} for _ in range(8)],
        'QF':  [{'home': None, 'away': None, 'winner': None} for _ in range(4)],
        'SF':  [{'home': None, 'away': None, 'winner': None} for _ in range(2)],
        'F':   [{'home': None, 'away': None, 'winner': None} for _ in range(1)]
    }
}

# --- CSATLAKOZÁS A GOOGLE TÁBLÁZATHOZ ---
worksheet = None
try:
    raw_key = st.secrets["google_credentials"]["private_key"]
    clean_key = raw_key.replace("\\n", "\n")
    
    creds_dict = {
        "type": "service_account",
        "project_id": "fifa-vb-projekt",
        "private_key_id": "2f6bc39019e239ba981dd32efc9ffe9f53843789",
        "private_key": clean_key,
        "client_email": "fifa-robot@fifa-vb-projekt.iam.gserviceaccount.com",
        "client_id": "109571828401921755693",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/raw/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/fifa-robot%40fifa-vb-projekt.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    gc = gspread.service_account_from_dict(creds_dict)
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/191B5mrm4MJrRX4dvpYyninsq3VwOnEpVoaK2UR03jTY/edit")
    worksheet = sh.worksheet("Munkalap1")
except Exception as e:
    if is_admin:
        st.sidebar.error("⚠️ Google Táblázat kapcsolat sikertelen, offline módban fut.")

# --- ADATKEZELŐ FÜGGVÉNYEK ---
def load_data():
    if worksheet is None:
        return DEFAULT_DATA
    try:
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            if "Adatok" in df.columns and not pd.isna(df["Adatok"].iloc[0]) and str(df["Adatok"].iloc[0]).strip():
                loaded = json.loads(df["Adatok"].iloc[0])
                if "matches" not in loaded: loaded["matches"] = []
                if "ko_state" not in loaded: loaded["ko_state"] = DEFAULT_DATA["ko_state"]
                return loaded
    except:
        pass
    return DEFAULT_DATA

def save_data():
    if worksheet is None:
        return
    mentes_dict = {"matches": st.session_state.matches, "ko_state": st.session_state.ko_state}
    try:
        worksheet.clear()
        worksheet.update(range_name="A1:A2", values=[["Adatok"], [json.dumps(mentes_dict, ensure_ascii=False)]])
    except Exception as e:
        if is_admin:
            st.error(f"Hiba a mentés során: {e}")

# --- ADATOK INICIALIZÁLÁSA ---
if 'matches' not in st.session_state or 'ko_state' not in st.session_state:
    data = load_data()
    st.session_state.matches = data.get("matches", [])
    st.session_state.ko_state = data.get("ko_state", DEFAULT_DATA["ko_state"])

def calculate_group_stats():
    stats = {team: {"M": 0, "Gy": 0, "D": 0, "V": 0, "RG": 0, "KG": 0, "GK": 0, "P": 0} for team in all_teams_list}
    for m in st.session_state.matches:
        if m.get('type') == 'group':
            h_team, a_team = m['home'], m['away']
            h_goals, a_goals = m['h_goals'], m['a_goals']
            if h_team in stats and a_team in stats:
                stats[h_team]["M"] += 1; stats[a_team]["M"] += 1
                stats[h_team]["RG"] += h_goals; stats[h_team]["KG"] += a_goals
                stats[a_team]["RG"] += a_goals; stats[a_team]["KG"] += h_goals
                if h_goals > a_goals:
                    stats[h_team]["Gy"] += 1; stats[h_team]["P"] += 3; stats[a_team]["V"] += 1
                elif a_goals > h_goals:
                    stats[a_team]["Gy"] += 1; stats[a_team]["P"] += 3; stats[h_team]["V"] += 1
                else:
                    stats[h_team]["D"] += 1; stats[a_team]["D"] += 1; stats[h_team]["P"] += 1; stats[a_team]["P"] += 1
    df = pd.DataFrame.from_dict(stats, orient='index')
    df['GK'] = df['RG'] - df['KG']
    return df

def get_all_scorers():
    scorers = {}
    for m in st.session_state.matches:
        for s in m.get('scorers', []):
            if s.strip(): scorers[s.strip()] = scorers.get(s.strip(), 0) + 1
    return scorers

def sort_group_teams_official(teams):
    df_all = calculate_group_stats()
    sub_df = df_all.loc[teams].copy()
    
    group_matches = []
    for m in st.session_state.matches:
        if m.get('type') == 'group' and m['home'] in teams and m['away'] in teams:
            group_matches.append(m)
            
    def get_h2h_score(t1, t2):
        pts, rg, kg = 0, 0, 0
        for m in group_matches:
            if m['home'] == t1 and m['away'] == t2:
                rg += m['h_goals']; kg += m['a_goals']
                if m['h_goals'] > m['a_goals']: pts += 3
                elif m['h_goals'] == m['a_goals']: pts += 1
            elif m['away'] == t1 and m['home'] == t2:
                rg += m['a_goals']; kg += m['h_goals']
                if m['a_goals'] > m['h_goals']: pts += 3
                elif m['a_goals'] == m['h_goals']: pts += 1
        return pts, rg - kg, rg

    sort_data = []
    for t in teams:
        row = sub_df.loc[t]
        h2h_p_sum, h2h_gk_sum, h2h_rg_sum = 0, 0, 0
        for opponent in teams:
            if opponent != t:
                if sub_df.loc[opponent]['P'] == row['P']:
                    p, gk, rg = get_h2h_score(t, opponent)
                    h2h_p_sum += p
                    h2h_gk_sum += gk
                    h2h_rg_sum += rg
                    
        sort_data.append({
            'team': t,
            'P': row['P'],
            'H2H_P': h2h_p_sum,
            'H2H_GK': h2h_gk_sum,
            'H2H_RG': h2h_rg_sum,
            'GK': row['GK'],
            'RG': row['RG']
        })
        
    sorted_structures = sorted(sort_data, key=lambda x: (x['P'], x['H2H_P'], x['H2H_GK'], x['H2H_RG'], x['GK'], x['RG']), reverse=True)
    return [x['team'] for x in sorted_structures]

def generate_valid_draw(seeded_unused, unseeded_unused):
    df_group = calculate_group_stats()
    group_results = {}
    all_3rds = []
    
    try:
        for g_name, g_teams in GROUPS.items():
            sorted_teams = sort_group_teams_official(g_teams)
            g_letter = g_name.split()[0]
            
            group_results[f"{g_letter}1"] = sorted_teams[0]
            group_results[f"{g_letter}2"] = sorted_teams[1]
            
            t3 = sorted_teams[2]
            row3 = df_group.loc[t3]
            all_3rds.append({
                'name': t3, 'group': g_letter,
                'P': row3['P'], 'GK': row3['GK'], 'RG': row3['RG']
            })
    except Exception:
        return None
    
    best_3rds_sorted = sorted(all_3rds, key=lambda x: (x['P'], x['GK'], x['RG']), reverse=True)[:8]
    m3 = {x['group']: x['name'] for x in best_3rds_sorted}
    
    def get_3rd(preferred_groups):
        for g in preferred_groups:
            if g in m3:
                val = m3[g]
                del m3[g]
                return val
        for g in list(m3.keys()):
            val = m3[g]
            del m3[g]
            return val
        return "Üres ág"

    matchups = []
    matchups.append((group_results.get("A1", "A1"), get_3rd(["C", "D", "E"])))
    matchups.append((group_results.get("B2", "B2"), group_results.get("F2", "F2")))
    matchups.append((group_results.get("E1", "E1"), get_3rd(["A", "B", "C", "D"])))
    matchups.append((group_results.get("F1", "F1"), group_results.get("G2", "G2")))
    
    matchups.append((group_results.get("C1", "C1"), get_3rd(["F", "G", "H"])))
    matchups.append((group_results.get("D2", "D2"), group_results.get("H2", "H2")))
    matchups.append((group_results.get("G1", "G1"), get_3rd(["E", "F", "H"])))
    matchups.append((group_results.get("I2", "I2"), group_results.get("J2", "J2")))
    
    matchups.append((group_results.get("B1", "B1"), get_3rd(["E", "F", "G"])))
    matchups.append((group_results.get("A2", "A2"), group_results.get("C2", "C2")))
    matchups.append((group_results.get("D1", "D1"), get_3rd(["I", "J", "K", "L"])))
    matchups.append((group_results.get("H1", "H1"), group_results.get("J2", "J2") if "J2" in group_results else group_results.get("L2", "L2")))
    
    matchups.append((group_results.get("I1", "I1"), get_3rd(["C", "D", "E", "F"])))
    matchups.append((group_results.get("E2", "E2"), group_results.get("K2", "K2") if "K2" in group_results else group_results.get("I2", "I2")))
    matchups.append((group_results.get("J1", "J1"), get_3rd(["G", "H", "I"])))
    matchups.append((group_results.get("K1", "K1"), group_results.get("L2", "L2")))
    
    return matchups

st.title("🏆 FIFA 2026 VB - Cloud Dashboard")
st.caption("Élő adatbázis kapcsolat: ✅ Online (Hivatalos FIFA 2026 Szabályzat)")

tab_group, tab_ko, tab_scorers = st.tabs(["📊 Csoportkör", "⚔️ Egyenes Kiesés", "🔥 Góllövőlista"])

with tab_group:
    col_input, col_table = st.columns([1, 2])
    with col_input:
        st.header("⚽ Csoportmeccs rögzítése")
        
        if is_admin:
            selected_group = st.selectbox("Válassz csoportot:", list(GROUPS.keys()))
            group_teams = GROUPS[selected_group]
            
            with st.form("group_match_form", clear_on_submit=True):
                home = st.selectbox("Hazai csapat", group_teams, key="h_sel")
                away = st.selectbox("Vendég csapat", group_teams, key="a_sel")
                g1, g2 = st.columns(2)
                h_goals = g1.number_input("Hazai gól", min_value=0, step=1)
                a_goals = g2.number_input("Vendég gól", min_value=0, step=1)
                scorer_input = st.text_area("Gólszerzők (vesszővel)", placeholder="Pl: Mbappe, Messi")
                
                if st.form_submit_button("Meccs mentése"):
                    if home == away:
                        st.error("Egy csapat nem játszhat önmaga ellen!")
                    else:
                        s_list = [s.strip() for s in scorer_input.split(",") if s.strip()]
                        st.session_state.matches.append({
                            "type": "group", "group": selected_group, "home": home, "away": away, 
                            "h_goals": h_goals, "a_goals": a_goals, "scorers": s_list
                        })
                        save_data()
                        st.success(f"Mentve: {home} {h_goals} - {a_goals} {away}")
                        st.rerun()
        else:
            st.info("A meccsek rögzítéséhez lépj be az oldalsávon!")

    with col_table:
        st.header("📊 Csoportok Állása")
        df_group = calculate_group_stats()
        group_tabs = st.tabs(list(GROUPS.keys()))
        for i, (g_name, g_teams) in enumerate(GROUPS.items()):
            with group_tabs[i]:
                ordered_teams = sort_group_teams_official(g_teams)
                sub_df = df_group.loc[ordered_teams].reset_index()
                sub_df.rename(columns={'index': 'Csapat'}, inplace=True)
                sub_df.index = range(1, len(sub_df) + 1)
                st.dataframe(sub_df, use_container_width=True)

with tab_ko:
    st.header("⚔️ Egyenes Kieséses Szakasz")
    
    total_group_matches = len([m for m in st.session_state.matches if m.get('type') == 'group'])
    
    if total_group_matches < 72:
        st.warning(f"⚠️ Eddig {total_group_matches} csoportmeccs lett rögzítve a 72-ből. A sorsolás gomb akkor lesz aktív, ha minden csoportmeccs véget ért!")
    
    if not st.session_state.ko_state.get('generated', False):
        if is_admin:
            disabled_status = True if total_group_matches < 72 else False
            if st.button("🚀 Hivatalos Sorsolás Generálása", type="primary", disabled=disabled_status):
                matchups = generate_valid_draw(None, None)
                
                if matchups:
                    for i, (h, a) in enumerate(matchups):
                        st.session_state.ko_state['R32'][i]['home'] = h
                        st.session_state.ko_state['R32'][i]['away'] = a
                    st.session_state.ko_state['generated'] = True
                    save_data()
                    st.rerun()
                else:
                    st.error("Hiba történt az ágrendszer felépítése során!")
        else:
            st.info("A sorsolást csak az admin tudja elindítani.")
            
    else:
        st.success("✅ A hivatalos FIFA 2026-os ágrendszer sikeresen legenerálva és mentve!")
        if is_admin:
            if st.button("Sorsolás törlése és Újragenerálás"):
                st.session_state.ko_state['generated'] = False
                save_data()
                st.rerun()

        rounds = [("Legjobb 32", "R32", "R16"), ("Nyolcaddöntő", "R16", "QF"), ("Negyeddöntő", "QF", "SF"), ("Elődöntő", "SF", "F"), ("🏆 Döntő", "F", None)]
        
        for round_name, current_key, next_key in rounds:
            with st.expander(f"{round_name}", expanded=True):
                for i, match in enumerate(st.session_state.ko_state[current_key]):
                    if match['home'] and match['away']:
                        if not match['winner']:
                            st.write(f"**{match['home']} 🆚 {match['away']}**")
                            if is_admin:
                                with st.form(f"form_{current_key}_{i}"):
                                    c1, c2, c3 = st.columns(3)
                                    h_g = c1.number_input(f"{match['home']} gól", 0, step=1)
                                    a_g = c2.number_input(f"{match['away']} gól", 0, step=1)
                                    default_idx = 0 if h_g >= a_g else 1
                                    winner = c3.selectbox("Továbbjutó", [match['home'], match['away']], index=default_idx)
                                    scorers = st.text_input("Gólszerzők (vesszővel)")
                                    
                                    if st.form_submit_button("Mentés"):
                                        st.session_state.ko_state[current_key][i]['winner'] = winner
                                        if scorers:
                                            st.session_state.matches.append({
                                                "type": "ko", "home": match['home'], "away": match['away'],
                                                "h_goals": h_g, "a_goals": a_g, 
                                                "scorers": [s.strip() for s in scorers.split(",") if s.strip()]
                                            })
                                        if next_key:
                                            next_idx = i // 2
                                            if i % 2 != 0: st.session_state.ko_state[next_key][next_idx]['away'] = winner
                                            else: st.session_state.ko_state[next_key][next_idx]['home'] = winner
                                        elif current_key == "F":
                                            st.balloons()
                                            st.success(f"🎉 A Világbajnok: {winner}! 🎉")
                                        save_data()
                                        st.rerun()
                        else:
                            st.info(f"✅ {match['home']} - {match['away']} | Továbbjutott: **{match['winner']}**")

with tab_scorers:
    st.header("🔥 Góllövőlista")
    scorers_dict = get_all_scorers()
    if scorers_dict:
        s_df = pd.DataFrame.from_dict(scorers_dict, orient='index', columns=['Gólok'])
        st.table(s_df.sort_values(by='Gólok', ascending=False))
    else:
        st.write("Még nincs rögzített gól.")

if st.session_state.matches:
    if is_admin:
        with st.sidebar.expander("🕒 Meccstörténet / Törlés"):
            for i, m in enumerate(st.session_state.matches):
                szakasz = m.get('group', 'Kieséses')
                col_text, col_btn = st.columns([4, 1])
                with col_text:
                    st.write(f"[{szakasz[:3]}] {m['home']} {m['h_goals']}-{m['a_goals']} {m['away']}")
                with col_btn:
                    if st.button("❌", key=f"del_match_{i}"):
                        st.session_state.matches.pop(i)
                        save_data()
                        st.rerun()
                        
            if st.button("🚨 Teljes törlés (VIGYÁZZ)"):
                st.session_state.matches = []
                st.session_state.ko_state['generated'] = False
                for k in ['R32', 'R16', 'QF', 'SF', 'F']:
                    for match in st.session_state.ko_state[k]:
                        match['home'] = match['away'] = match['winner'] = None
                save_data()
                st.rerun()
    else:
        with st.sidebar.expander("🕒 Meccstörténet"):
            for i, m in enumerate(st.session_state.matches):
                szakasz = m.get('group', 'Kieséses')
                st.write(f"[{szakasz[:3]}] {m['home']} {m['h_goals']}-{m['a_goals']} {m['away']}")
