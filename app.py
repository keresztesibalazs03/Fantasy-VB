import streamlit as st
import pandas as pd
import random
import json
import gspread

st.set_page_config(page_title="Hivatalos FIFA 2026 VB Dashboard", layout="wide")

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
    # 3. A HIVATALOS FIFA 2026-OS MECCSTÁBLA (Legjobb 32 fix párosításai)
    matchups = []
    matchups.append((group_results["A1"], get_3rd(["C", "D", "E"])))
    matchups.append((group_results["B2"], group_results["F2"]))
    matchups.append((group_results["E1"], get_3rd(["A", "B", "C", "D"])))
    matchups.append((group_results["F1"], group_results["G2"]))
    
    matchups.append((group_results["C1"], get_3rd(["F", "G", "H"])))
    matchups.append((group_results["D2"], group_results["H2"]))
    matchups.append((group_results["G1"], get_3rd(["E", "F", "H"])))
    matchups.append((group_results["I2"], group_results["J2"]))
    
    matchups.append((group_results["B1"], get_3rd(["E", "F", "G"])))
    matchups.append((group_results["A2"], group_results["C2"]))
    matchups.append((group_results["D1"], get_3rd(["I", "J", "K", "L"])))
    matchups.append((group_results["H1"], get_3rd(["J", "K", "L"])))
    
    matchups.append((group_results["I1"], get_3rd(["C", "D", "E", "F"])))
    matchups.append((group_results["E2"], group_results["K2"]))
    matchups.append((group_results["J1"], get_3rd(["G", "H", "I"])))
    matchups.append((group_results["K1"], group_results["L2"]))
    
    return matchups
