import streamlit as st
import pandas as pd
import random
import json
import gspread

st.set_page_config(page_title="Hivatalos FIFA 2026 VB Dashboard", layout="wide")

# --- CSATLAKOZÁS A GOOGLE TÁBLÁZATHOZ (STABIL GSPREAD VERZIÓ) ---
try:
    creds_dict = json.loads(st.secrets["google_credentials"]["json"])
    gc = gspread.service_account_from_dict(creds_dict)
    # Megnyitjuk a táblázatot az URL alapján
    sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/191B5mrm4MJrRX4dvpYyninsq3VwOnEpVoaK2UR03jTY/edit")
    worksheet = sh.worksheet("Munkalap1")
except Exception as e:
    st.error(f"Nem sikerült csatlakozni a Google Táblázathoz: {e}")
    st.stop()

# --- ADATKEZELŐ FÜGGVÉNYEK (JAVÍTOTT, TISZTA VERZIÓK) ---
def load_data():
    global worksheet
    try:
        # Beolvassuk az összes adatot a Munkalap1-ről
        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            if "Adatok" in df.columns and not pd.isna(df["Adatok"].iloc[0]):
                return json.loads(df["Adatok"].iloc[0])
    except:
        pass
    return {
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

def save_data():
    global worksheet
    mentes_dict = {"matches": st.session_state.matches, "ko_state": st.session_state.ko_state}
    # Töröljük a régi tartalmat és beírjuk az újat
    worksheet.clear()
    # Gspread-nél fejléc + érték kell listaként
    worksheet.update(range_name="A1:A2", values=[["Adatok"], [json.dumps(mentes_dict, ensure_ascii=False)]])

# --- ADATOK INICIALIZÁLÁSA ---
if 'matches' not in st.session_state or 'ko_state' not in st.session_state:
    data = load_data()
    st.session_state.matches = data["matches"]
    st.session_state.ko_state = data["ko_state"]

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
        for s in m['scorers']:
            if s.strip(): scorers[s.strip()] = scorers.get(s.strip(), 0) + 1
    return scorers

def generate_valid_draw(seeded, unseeded):
    for _ in range(2000):
        random.shuffle(unseeded)
        valid = True
        for i in range(16):
            if seeded[i]['group'] == unseeded[i]['group']:
                valid = False
                break
        if valid: return [(seeded[i]['name'], unseeded[i]['name']) for i in range(16)]
    return None

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
        df_group = calculate_group_stats
