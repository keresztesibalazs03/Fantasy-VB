import streamlit as st
import pandas as pd
import random
import json
import gspread

st.set_page_config(page_title="Hivatalos FIFA 2026 VB Dashboard", layout="wide")

# --- HIVATALOS 2026-OS VB CSOPORTOK (Előrehozva, hogy minden függvény lássa) ---
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

# --- CSATLAKOZÁS A GOOGLE TÁBLÁZATHOZ (BEÉGETETT URL VERZIÓ) ---
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
    import traceback
    st.error("Nem sikerült csatlakozni a Google Táblázathoz:")
    st.code(traceback.format_exc())
    st.stop()

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

# --- ADATKEZELŐ FÜGGVÉNYEK ---
def load_data():
    global worksheet
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
    global worksheet
    mentes_dict = {"matches": st.session_state.matches, "ko_state": st.session_state.ko_state}
    try:
        worksheet.clear()
        worksheet.update(range_name="A1:A2", values=[["Adatok"], [json.dumps(mentes_dict, ensure_ascii=False)]])
    except Exception as e:
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

# --- HIVATALOS FIFA 2026-OS ÁGRENDSZER GENERÁLÓ ---
def generate_valid_draw(seeded_unused, unseeded_unused):
    df_group = calculate_group_stats()
    group_results = {}
    all_3rds = []
    
    try:
        # 1. Kigyűjtjük az összes csoport 1., 2. helyezettjét betűk alapján (A, B, C...)
        for g_name, g_teams in GROUPS.items():
            sub_df = df_group.loc[g_teams].sort_values(by=['P', 'GK', 'RG'], ascending=False).reset_index()
            g_letter = g_name.split()[0]  # Kinyeri az "A", "B" stb. betűt
            group_results[f"{g_letter}1"] = sub_df.iloc[0]['index']
            group_results[f"{g_letter}2"] = sub_df.iloc[1]['index']
            all_3rds.append({
                'name': sub_df.iloc[2]['index'], 'group': g_letter,
                'P': sub_df.iloc[2]['P'], 'GK': sub_df.iloc[2]['GK'], 'RG': sub_df.iloc[2]['RG']
            })
    except Exception:
        return None
    
    # 2. Kiválasztjuk a 8 legjobb csoportharmadikat teljesítmény szerint
    best_3rds_sorted = sorted(all_3rds, key=lambda x: (x['P'], x['GK'], x['RG']), reverse=True)[:8]
    m3 = {x['group']: x['name'] for x in best_3rds_sorted}
    
    # Kiosztó logika a FIFA prioritási listája alapján
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

    # 3. A HIVATALOS FIFA 2026-OS MECCSTÁBLA (Legjobb 32 fix párosításai)
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
st.caption("Élő adatbázis kapcsolat: ✅ Online")

tab_group, tab_ko, tab_scorers = st.tabs(["📊 Csoportkör", "⚔️ Egyenes Kiesés", "🔥 Góllövőlista"])

with tab_group:
    col_input, col_table = st.columns([1, 2])
    with col_input:
        st.header("⚽ Csoportmeccs rögzítése")
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

    with col_table:
        st.header("📊 Csoportok Állása")
        df_group = calculate_group_stats()
        group_tabs = st.tabs(list(GROUPS.keys()))
        for i, (g_name, g_teams) in enumerate(GROUPS.items()):
            with group_tabs[i]:
                sub_df = df_group.loc[g_teams].sort_values(by=['P', 'GK', 'RG'], ascending=False).reset_index()
                sub_df.rename(columns={'index': 'Csapat'}, inplace=True)
                sub_df.index = range(1, len(sub_df) + 1)
                st.dataframe(sub_df, use_container_width=True)

with tab_ko:
    st.header("⚔️ Egyenes Kieséses Szakasz")
    
    # Ellenőrizzük, hogy van-e már rögzített csoportmeccs egyáltalán
    df_group = calculate_group_stats()
    total_group_matches = len([m for m in st.session_state.matches if m.get('type') == 'group'])
    
    # 12 csoport van, csoportonként 6 meccs = összesen 72 meccs lenne a teljes kör, 
    # de engedjük sorsolni akkor is, ha már van benne adat (vagy ha teljesen kész)
    if total_group_matches < 72:
        st.warning(f"⚠️ Eddig {total_group_matches} csoportmeccs lett rögzítve a 72-ből. A hivatalos sorsolás gomb akkor lesz aktív, ha minden csoportmeccs véget ért!")
    
    if not st.session_state.ko_state.get('generated', False):
        # Csak akkor engedjük megnyomni, ha lejátszották a csoportkört, nehogy véletlenül üres táblát sorsoljon
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
        st.success("✅ A hivatalos FIFA 2026-os ágrendszer sikeresen legenerálva és mentve!")
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
                            with st.form(f"form_{current_key}_{i}"):
                                st.write(f"**{match['home']} 🆚 {match['away']}**")
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
