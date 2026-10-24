import csv
import io
import json
from datetime import date
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='SPORT EDGE AI · v0.8', page_icon='📈', layout='wide')
st.title('SPORT EDGE AI')
st.caption('v0.8 · HRB Market Intelligence · Datos y probabilidades manuales donde se indique · Sin apuestas automáticas')
LEAGUES = {'MLB': ('baseball','mlb'), 'NHL': ('hockey','nhl'), 'NBA': ('basketball','nba'), 'NFL': ('football','nfl'), 'NCAAF': ('football','college-football'), 'Soccer': ('soccer','eng.1')}
SOCCER_LEAGUES = {'Premier League': 'eng.1', 'LaLiga': 'esp.1', 'Serie A': 'ita.1', 'Bundesliga': 'ger.1', 'Ligue 1': 'fra.1', 'Champions League': 'uefa.champions', 'Europa League': 'uefa.europa', 'MLS': 'usa.1'}
DATA_FILE = Path(__file__).parent / 'bets.csv'
FIELDS = ['fecha','deporte','partido','mercado','seleccion','cuota','stake','resultado']

def dec(american):
    if american == 0: raise ValueError('La cuota americana no puede ser cero')
    return 1 + american/100 if american > 0 else 1 + 100/abs(american)

def read_bets():
    if not DATA_FILE.exists(): return pd.DataFrame(columns=FIELDS)
    return pd.read_csv(DATA_FILE).fillna('')

def payout_profit(odds, stake, result):
    if result == 'Ganada': return stake*(dec(odds)-1)
    if result == 'Perdida': return -stake
    return 0.0

@st.cache_data(ttl=900, show_spinner=False)
def events(league, day, soccer_slug=None):
    sport, slug = LEAGUES[league]
    if league == "Soccer" and soccer_slug:
        slug = soccer_slug
    url = f'https://site.api.espn.com/apis/site/v2/sports/{sport}/{slug}/scoreboard'
    response = requests.get(url, params={'dates': day.strftime('%Y%m%d'), 'limit': 100}, timeout=12)
    response.raise_for_status()
    payload = response.json()
    rows=[]
    for ev in payload.get('events', []):
        comp=(ev.get('competitions') or [{}])[0]
        teams=comp.get('competitors') or []
        away=next((t for t in teams if t.get('homeAway')=='away'),{})
        home=next((t for t in teams if t.get('homeAway')=='home'),{})
        rows.append({'Inicio (Miami)':pd.to_datetime(ev.get('date'), utc=True).tz_convert('America/New_York').strftime('%Y-%m-%d %I:%M %p') if ev.get('date') else '', 'Visitante':away.get('team',{}).get('displayName',''), 'Local':home.get('team',{}).get('displayName',''), 'Estado':ev.get('status',{}).get('type',{}).get('description',''), 'Marcador':f"{away.get('score','–')} - {home.get('score','–')}"})
    return rows

league=st.selectbox('Deporte',list(LEAGUES))
soccer_slug = None
if league == 'Soccer':
    soccer_competition = st.selectbox('Competición de fútbol', list(SOCCER_LEAGUES))
    soccer_slug = SOCCER_LEAGUES[soccer_competition]
t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11=st.tabs(['📅 Sports Dashboard','📊 Betting Analyzer','🧩 Parlay Builder','📒 Bet Tracker','🎯 HRB Market Scanner','🧠 NBA / NFL Models','⭐ Best Parlay 2–20','🔎 Analyze All Games','📈 Team Form & Matchups','🛡️ EDGE Risk Shield','📉 Performance Lab'])
with t1:
    st.subheader('Partidos y resultados')
    d=st.date_input('Fecha', value=date.today(), key='schedule_date')
    st.caption('Fuente pública de calendario/resultados de ESPN (endpoint no oficial, sin garantía de disponibilidad). No incluye cuotas de Hard Rock Bet.')
    if st.button('Consultar partidos'):
        try:
            rows=events(league,d,soccer_slug)
            if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
            else: st.info('No se encontraron partidos para esa fecha y liga.')
        except (requests.RequestException, ValueError, KeyError) as ex:
            st.warning(f'No se pudo consultar el calendario: {ex}')
with t2:
    st.subheader('Evaluación matemática de una selección')
    a,b=st.columns(2)
    with a:
        market=st.text_input('Mercado',value='Moneyline')
        american=st.number_input('Cuota americana',value=-110,step=5)
    with b:
        p=st.slider('Probabilidad estimada manual (%)',min_value=1,max_value=99,value=55)/100
        stake=st.number_input('Monto ($)',min_value=0.01,value=10.0,step=5.0)
    decimal=dec(american)
    implied=1/decimal
    ev=p*stake*(decimal-1)-(1-p)*stake
    c1,c2,c3=st.columns(3)
    c1.metric('Probabilidad implícita',f'{implied:.2%}')
    c2.metric('Punto de equilibrio',f'{implied:.2%}')
    c3.metric('Valor esperado estimado',f'${ev:+.2f}')
    st.info('La probabilidad es una estimación introducida por ti. El EV depende de que esa estimación sea correcta; no es una predicción del sistema.')
with t3:
    st.subheader('Constructor de parlays (2–20)')
    st.caption('Introduce cada selección y su cuota. Las probabilidades individuales son manuales. No se garantiza compatibilidad con SGP/SGP Max.')
    count=st.number_input('Número de selecciones',min_value=2,max_value=20,value=4,step=1)
    initial=pd.DataFrame([{'Partido':f'Juego {i+1}','Selección':'','Cuota americana':-110,'Probabilidad (%)':60} for i in range(int(count))])
    editor=st.data_editor(initial, num_rows='fixed', use_container_width=True,hide_index=True,key=f'parlay_{count}')
    try:
        odds=[int(x) for x in editor['Cuota americana']]
        probs=[float(x)/100 for x in editor['Probabilidad (%)']]
        if any(not 0 < p < 1 for p in probs): raise ValueError('Las probabilidades deben estar entre 1 y 99%.')
        combined=1.0
        for o in odds: combined*=dec(o)
        joint=1.0
        for p in probs: joint*=p
        american_combined=round((combined-1)*100) if combined>=2 else round(-100/(combined-1))
        x,y,z=st.columns(3)
        x.metric('Cuota decimal combinada',f'{combined:.2f}')
        y.metric('Cuota americana aproximada',f'{american_combined:+d}')
        z.metric('Probabilidad conjunta*',f'{joint:.3%}')
        st.warning('*La probabilidad conjunta supone independencia. Si hay selecciones relacionadas, especialmente en un mismo partido, NO es una estimación válida. Las cuotas también pueden diferir de las ofrecidas por HRB para parlays correlacionados.')
        st.download_button('Exportar selecciones CSV',editor.to_csv(index=False).encode('utf-8-sig'),'parlay_sport_edge.csv','text/csv')
    except (ValueError, TypeError, ZeroDivisionError) as e:
        st.error(f'Revisa las cuotas y probabilidades: {e}')
with t4:
    st.subheader('Registro local de apuestas')
    with st.form('add_bet'):
        d=st.date_input('Fecha de la apuesta',value=date.today(),key='bet_date')
        game=st.text_input('Partido')
        market=st.text_input('Mercado',value='Moneyline',key='bet_market')
        pick=st.text_input('Selección')
        a,b,c=st.columns(3)
        with a: o=st.number_input('Cuota',value=-110,step=5,key='bet_odds')
        with b: s=st.number_input('Stake ($)',min_value=0.01,value=10.0,step=1.0,key='bet_stake')
        with c: outcome=st.selectbox('Resultado',['Pendiente','Ganada','Perdida','Nula'])
        save=st.form_submit_button('Guardar apuesta')
    if save:
        if not game.strip() or not pick.strip(): st.error('Completa partido y selección.')
        else:
            with DATA_FILE.open('a',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=FIELDS)
                if f.tell()==0: writer.writeheader()
                writer.writerow(dict(zip(FIELDS,[d.isoformat(),league,game,market,pick,o,s,outcome])))
            st.success('Apuesta guardada en este servidor. En hosting gratuito los archivos locales podrían perderse al reiniciar.')
    df=read_bets()
    if len(df):
        st.dataframe(df,use_container_width=True,hide_index=True)
        settled=df[df['resultado'].isin(['Ganada','Perdida','Nula'])].copy()
        if len(settled):
            profit=sum(payout_profit(float(row['cuota']),float(row['stake']),row['resultado']) for _,row in settled.iterrows())
            risked=sum(float(row['stake']) for _,row in settled.iterrows() if row['resultado'] in ('Ganada','Perdida'))
            st.metric('Beneficio neto realizado',f'${profit:+.2f}')
            st.metric('ROI sobre stakes resueltos',f'{profit/risked:.2%}' if risked else 'N/D')
        st.download_button('Descargar registro CSV',df.to_csv(index=False).encode('utf-8-sig'),'registro_sport_edge.csv','text/csv')
    else: st.info('Todavía no hay apuestas registradas.')

# Catálogo de mercados candidatos: NO representa disponibilidad confirmada en HRB.
MARKETS = {
 'MLB': {'Partido':['Moneyline','Run Line','Total Runs','Team Total Runs','First 5 Innings ML','First 5 Innings Total'], 'Jugadores':['Hits','Runs','RBI','Hits + Runs + RBI','Total Bases','Home Runs','Strikeouts (pitcher)','Walks (batter)','Pitcher Outs']},
 'NHL': {'Partido':['Moneyline','3-Way Moneyline','Puck Line','Total Goals','Team Total Goals','1st Period Total'], 'Jugadores':['Shots on Goal','Points','Goals','Assists','Goalie Saves']},
 'NBA': {'Partido':['Moneyline','Spread','Game Total','Team Total','1st Half Spread','1st Quarter Total'], 'Jugadores':['Points','Rebounds','Assists','3-Pointers Made','Points + Rebounds + Assists','Points + Assists','Double-Double']},
 'NFL': {'Partido':['Moneyline','Spread','Game Total','Team Total','1st Half Total'], 'Jugadores':['Passing TDs','Passing Yards','Rushing Yards','Receiving Yards','Receptions','Anytime TD','First TD','Longest Reception','Pass Completions']},
 'NCAAF': {'Partido':['Moneyline','Spread','Game Total','Team Total','1st Half Spread'], 'Jugadores':['Passing TDs','Passing Yards','Rushing Yards','Receiving Yards','Anytime TD','Receptions']},
 'Soccer': {'Partido':['1X2','Double Chance','Draw No Bet','Asian Handicap','Total Goals','Both Teams to Score','Team Total Goals','Corners','Cards','Correct Score'], 'Jugadores':['Anytime Goalscorer','Shots','Shots on Target','Assists']}
}

def pct_odds(american):
    return 1.0 / dec(american)

def market_assessment(probability, american):
    decimal = dec(american)
    implied = 1 / decimal
    roi = probability * decimal - 1
    return implied, roi, (probability - implied)

with t5:
    st.subheader('HRB Market Scanner · comparador de alternativas')
    st.warning('Catálogo orientativo, no una lista de mercados confirmados de Hard Rock Bet. Introduce únicamente cuotas que hayas visto en HRB. No tenemos acceso a su cuenta ni a sus cuotas en vivo.')
    group = st.selectbox('Tipo de mercado', list(MARKETS[league]), key='market_group')
    market_options = MARKETS[league][group]
    selected_market = st.selectbox('Mercado de referencia', market_options, key='reference_market')
    st.caption('Puedes comparar diferentes líneas, mercados y jugadores. Una probabilidad manual incorrecta produce un valor esperado incorrecto.')
    n = st.slider('Alternativas a comparar', 2, 12, 4, key='market_count')
    starting = pd.DataFrame([{'Partido / jugador':'', 'Mercado': selected_market, 'Línea / selección':'', 'Cuota HRB':-110, 'Probabilidad manual (%)':50, 'Lesión / lineup':'Sin verificar', 'Fuente / hora cuota':''} for _ in range(n)])
    choices = st.data_editor(starting, hide_index=True, num_rows='fixed', use_container_width=True, key=f'market_editor_{league}_{group}_{n}')
    if st.button('Evaluar alternativas', type='primary'):
        try:
            results = []
            for _, row in choices.iterrows():
                american = int(row['Cuota HRB'])
                prob = float(row['Probabilidad manual (%)'])/100
                if not 0 < prob < 1: raise ValueError('La probabilidad debe estar entre 0 y 100, sin incluir extremos.')
                implied, roi, edge = market_assessment(prob, american)
                label = str(row['Partido / jugador']).strip() or '(sin identificar)'
                results.append({'Partido / jugador':label, 'Mercado':str(row['Mercado']), 'Selección':str(row['Línea / selección']), 'Cuota HRB':american, 'Prob. implícita':f'{implied:.1%}', 'Prob. manual':f'{prob:.1%}', 'Edge estimado':f'{edge:+.1%}', 'EV por $100':f'${roi*100:+.2f}', 'ROI teórico':roi, 'Disponibilidad':str(row['Lesión / lineup']), 'Fuente / hora':str(row['Fuente / hora cuota'])})
            results.sort(key=lambda x: x['ROI teórico'], reverse=True)
            for row in results: row.pop('ROI teórico')
            st.dataframe(pd.DataFrame(results), hide_index=True, use_container_width=True)
            st.download_button('Exportar comparación CSV', pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig'), 'sport_edge_market_comparison.csv', 'text/csv')
            st.info('Ordenado por EV estimado, NO por certeza de ganar. Antes de jugar, confirma mercado, cuota, alineación, lesiones, reglas de liquidación y elegibilidad de parlay en HRB.')
        except (ValueError, TypeError, ZeroDivisionError) as ex:
            st.error(f'Corrige los datos: {ex}')
    with st.expander('Checklist de calidad antes de agregar una selección'):
        st.markdown("""- [ ] Mercado y línea disponibles realmente en HRB.
- [ ] Cuota capturada con fecha/hora (puede cambiar).
- [ ] Jugador confirmado y sin restricción importante de minutos o snaps.
- [ ] Lesiones, rotaciones, portero/pitcher y alineación verificadas.
- [ ] Reglas de liquidación y prórroga revisadas.
- [ ] Modelo validado históricamente para ese deporte y mercado.
- [ ] No se confundió probabilidad alta con valor esperado positivo.
- [ ] Correlación y compatibilidad SGP verificadas en la app de HRB.
- [ ] No se fuerza un número de selecciones para completar el parlay.
- [ ] Exposición y límite de gasto definidos antes de apostar.""")

st.divider()
st.caption('SPORT EDGE AI v0.8 · Mercados candidatos, NO disponibilidad confirmada en HRB · Sin conexión a HRB, apuestas automáticas, predicciones calibradas ni Telegram.')

# v0.8: modelos exploratorios parametrizados. No son predicciones calibradas.
import math
from itertools import combinations

def normal_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def poisson_at_least(k, lam):
    if k <= 0: return 1.0
    return max(0.0, min(1.0, 1 - math.exp(-lam) * sum(lam**i / math.factorial(i) for i in range(k))))

with t6:
    st.subheader("Modelos exploratorios NBA / NFL")
    st.warning("Estos modelos son calculadoras estadísticas con parámetros MANUALES, no pronósticos entrenados, calibrados ni basados en datos de jugadores en vivo.")
    if league not in ("NBA", "NFL"):
        st.info("Selecciona NBA o NFL en el selector superior para utilizar este módulo.")
    elif league == "NBA":
        st.markdown("**NBA · Probabilidad de superar una línea estadística**")
        a, b, c = st.columns(3)
        with a: mean = st.number_input("Media proyectada manual", 0.0, 100.0, 24.0, 0.5, key="nba_mu")
        with b: sd = st.number_input("Desviación estándar manual", 0.1, 50.0, 7.0, 0.5, key="nba_sd")
        with c: line = st.number_input("Línea Over", 0.0, 100.0, 22.5, 0.5, key="nba_line")
        p_over = 1 - normal_cdf((line - mean) / sd)
        st.metric("P(Over) · aproximación normal", f"{p_over:.1%}")
        st.caption("La aproximación normal puede ser inadecuada para ciertos mercados. No incluye lesiones, minutos ni matchup automáticamente.")
    else:
        st.markdown("**NFL · Probabilidad de alcanzar touchdowns por pase**")
        lam = st.number_input("Passing TDs esperados (media manual)", 0.01, 8.0, 1.7, 0.1, key="nfl_lambda")
        k = st.selectbox("Línea", [1, 2, 3, 4], key="nfl_k")
        st.metric(f"P({k}+ Passing TDs) · Poisson", f"{poisson_at_least(k, lam):.1%}")
        st.caption("Poisson es una simplificación. La media no se estima automáticamente y el modelo no está calibrado.")

with t7:
    st.subheader("Best Parlay · 2 a 20 selecciones")
    st.caption("Carga candidatas con cuota y probabilidad estimada. La herramienta busca el subconjunto con mayor valor esperado matemático entre selecciones de partidos DISTINTOS.")
    st.warning("No valida cuotas, mercados ni compatibilidad SGP de HRB. No garantiza resultados; las probabilidades son manuales y la independencia entre partidos es una simplificación.")
    num = st.number_input("Número de candidatas", min_value=2, max_value=30, value=6, step=1, key="optimizer_n")
    target = st.slider("Máximo de selecciones por parlay", 2, 20, 6, key="optimizer_max")
    min_legs = st.slider("Mínimo de selecciones", 2, target, 2, key="optimizer_min")
    template = pd.DataFrame([{
        "Partido (ID único)": f"Juego {i+1}",
        "Jugador / equipo": "",
        "Mercado y línea": "",
        "Cuota americana": -110,
        "Probabilidad manual (%)": 55.0,
        "Verificado en HRB": False
    } for i in range(num)])
    candidates = st.data_editor(template, use_container_width=True, hide_index=True,
                                num_rows="fixed", key=f"optimizer_editor_{num}")
    only_verified = st.checkbox("Usar solamente selecciones verificadas en HRB", value=True)
    if st.button("Buscar mejores combinaciones", type="primary", key="run_optimizer"):
        try:
            options = []
            for _, row in candidates.iterrows():
                if only_verified and not bool(row["Verificado en HRB"]):
                    continue
                p = float(row["Probabilidad manual (%)"]) / 100
                o = int(row["Cuota americana"])
                if not 0 < p < 1: raise ValueError("Cada probabilidad debe estar entre 0 y 100%.")
                if o == 0: raise ValueError("La cuota no puede ser cero.")
                game = str(row["Partido (ID único)"]).strip()
                if not game: raise ValueError("Cada candidata debe identificar su partido.")
                options.append((game, str(row["Jugador / equipo"]), str(row["Mercado y línea"]), o, p))
            if len(options) < min_legs:
                st.error("No hay suficientes selecciones elegibles. Marca 'Verificado en HRB' o desactiva el filtro para una simulación.")
            else:
                # Una selección por partido: no resuelve correlación entre partidos ni garantiza independencia.
                # Enumeración limitada a 30 candidatas; selección heurística por EV individual para evitar combinatoria explosiva.
                ranked = sorted(options, key=lambda x: x[4] * dec(x[3]), reverse=True)
                best_by_game = {}
                for item in ranked:
                    if item[0] not in best_by_game: best_by_game[item[0]] = item
                pool = list(best_by_game.values())
                results = []
                # Para cada tamaño, los mejores k productos p*cuota maximizan el EV conjunto bajo independencia.
                for k in range(min_legs, min(target, len(pool)) + 1):
                    chosen = pool[:k]
                    joint_p = math.prod(x[4] for x in chosen)
                    joint_odds = math.prod(dec(x[3]) for x in chosen)
                    ev_roi = joint_p * joint_odds - 1
                    results.append((k, ev_roi, joint_p, joint_odds, chosen))
                if not results:
                    st.error("Se necesitan al menos dos partidos diferentes.")
                else:
                    results.sort(key=lambda x: x[1], reverse=True)
                    k, roi, prob, odds, chosen = results[0]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Selecciones", str(k))
                    c2.metric("Probabilidad conjunta*", f"{prob:.3%}")
                    c3.metric("EV por $100*", f"${roi*100:+.2f}")
                    st.metric("Cuota decimal combinada (teórica)", f"{odds:.2f}")
                    st.dataframe(pd.DataFrame(chosen, columns=["Partido", "Jugador/equipo", "Mercado", "Cuota americana", "Probabilidad manual (0–1)"]), hide_index=True, use_container_width=True)
                    st.markdown("**Alternativas por cantidad de selecciones**")
                    st.dataframe(pd.DataFrame([{"Legs": x[0], "Probabilidad conjunta*": f"{x[2]:.3%}", "EV por $100*": f"${x[1]*100:+.2f}"} for x in sorted(results, key=lambda z: z[0])]), hide_index=True, use_container_width=True)
                    st.warning("*Cálculo condicionado a probabilidades manuales e independencia. Los resultados pueden ser muy engañosos si los supuestos son incorrectos. HRB puede rechazar la combinación o ofrecer otra cuota.")
        except (ValueError, TypeError, OverflowError) as exc:
            st.error(f"Corrige los datos: {exc}")


# v0.8 — Exploración automática de toda la jornada (NBA y NFL).
# La API pública de ESPN no es una fuente oficial ni un proveedor de cuotas HRB.
@st.cache_data(ttl=900, show_spinner=False)
def get_full_scoreboard(sport_key, slug, selected_day):
    endpoint = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{slug}/scoreboard"
    response = requests.get(endpoint, params={"dates": selected_day.strftime("%Y%m%d"), "limit": 100}, timeout=15)
    response.raise_for_status()
    return response.json().get("events", [])

@st.cache_data(ttl=900, show_spinner=False)
def get_event_summary(sport_key, slug, event_id):
    endpoint = f"https://site.api.espn.com/apis/site/v2/sports/{sport_key}/{slug}/summary"
    response = requests.get(endpoint, params={"event": event_id}, timeout=15)
    response.raise_for_status()
    return response.json()

def competitor_info(c):
    team = c.get("team") or {}
    records = c.get("records") or []
    record = ", ".join(str(x.get("summary", "")) for x in records if x.get("summary"))
    return {"Equipo": team.get("displayName", "N/D"), "Localía": "Local" if c.get("homeAway") == "home" else "Visitante", "Récord publicado": record or "No disponible", "Puntos": c.get("score", "—")}

def player_leaders_from_summary(summary):
    result = []
    for team_group in (summary.get("leaders") or []):
        team_name = (team_group.get("team") or {}).get("displayName", "")
        for category in (team_group.get("leaders") or []):
            category_name = category.get("displayName") or category.get("name") or "Estadística"
            for item in (category.get("leaders") or [])[:3]:
                athlete = item.get("athlete") or {}
                value = item.get("displayValue", "")
                if athlete.get("displayName"):
                    result.append({"Equipo": team_name, "Jugador": athlete.get("displayName"), "Categoría": category_name, "Valor ESPN": value})
    return result

with t8:
    st.subheader("Analyze All Games · NBA / NFL")
    st.caption("Consulta todos los partidos de la fecha seleccionada y muestra información disponible por partido. No genera picks ni probabilidades automáticas.")
    if league not in ("NBA", "NFL"):
        st.info("Selecciona NBA o NFL en el menú Deporte para utilizar este módulo.")
    else:
        scan_day = st.date_input("Fecha para analizar toda la jornada", value=date.today(), key="scan_day")
        load_detail = st.checkbox("Consultar detalles y líderes disponibles de ESPN", value=False, key="scan_detail")
        st.caption("Los líderes publicados pueden ser históricos, de temporada o del propio partido según el evento. No son proyecciones ni líneas de HRB.")
        if st.button("🔎 Analyze All Games", type="primary", key="scan_all"):
            try:
                sport_key, slug = LEAGUES[league]
                games = get_full_scoreboard(sport_key, slug, scan_day)
                if not games:
                    st.info("No hay partidos disponibles en ESPN para esta fecha.")
                else:
                    st.success(f"Se encontraron {len(games)} partidos de {league}.")
                    for game in games:
                        comp = (game.get("competitions") or [{}])[0]
                        teams = comp.get("competitors") or []
                        away = next((c for c in teams if c.get("homeAway") == "away"), {})
                        home = next((c for c in teams if c.get("homeAway") == "home"), {})
                        away_name = (away.get("team") or {}).get("displayName", "Visitante")
                        home_name = (home.get("team") or {}).get("displayName", "Local")
                        dt = pd.to_datetime(game.get("date"), utc=True, errors="coerce")
                        when = dt.tz_convert("America/New_York").strftime("%d/%m %I:%M %p") if pd.notna(dt) else "Horario no disponible"
                        status = (game.get("status") or {}).get("type", {}).get("description", "")
                        with st.expander(f"{away_name} @ {home_name} · {when} · {status}"):
                            st.dataframe(pd.DataFrame([competitor_info(away), competitor_info(home)]), hide_index=True, use_container_width=True)
                            st.caption("Los récords y marcadores son datos publicados por ESPN. Pueden no estar disponibles antes del encuentro.")
                            if load_detail and game.get("id"):
                                try:
                                    summary = get_event_summary(sport_key, slug, str(game["id"]))
                                    leaders = player_leaders_from_summary(summary)
                                    if leaders:
                                        st.markdown("**Jugadores destacados publicados por ESPN**")
                                        st.dataframe(pd.DataFrame(leaders), hide_index=True, use_container_width=True)
                                    else:
                                        st.info("ESPN no proporciona líderes individuales para este partido en el formato consultado.")
                                except (requests.RequestException, ValueError, KeyError) as exc:
                                    st.warning(f"No se pudieron obtener los detalles: {exc}")
                    st.info("Siguiente fase: estadísticas históricas, proyecciones validadas, lesiones y cuotas verificadas de HRB. Sin esas piezas no es posible ordenar apuestas por valor real.")
            except (requests.RequestException, ValueError, KeyError) as exc:
                st.error(f"No se pudo completar la consulta: {exc}")


# v0.8 — Team Form: resultados pasados, sin datos futuros ni predicciones inventadas.
from datetime import timedelta

@st.cache_data(ttl=1800, show_spinner=False)
def historical_scoreboards(sport_key, slug, target_day, days):
    """Consulta un día por solicitud: más fiable que asumir soporte de rangos."""
    games = []
    failures = []
    for offset in range(1, days + 1):
        past_day = target_day - timedelta(days=offset)
        try:
            games.extend(get_full_scoreboard(sport_key, slug, past_day))
        except (requests.RequestException, ValueError, KeyError) as exc:
            failures.append(f"{past_day.isoformat()}: {exc}")
    return games, failures

def team_form(games, team_id, limit=10):
    completed = []
    seen = set()
    for game in games:
        gid = str(game.get("id", ""))
        if not gid or gid in seen:
            continue
        seen.add(gid)
        status = (game.get("status") or {}).get("type") or {}
        if not status.get("completed"):
            continue
        comp = (game.get("competitions") or [{}])[0]
        teams = comp.get("competitors") or []
        ours = next((c for c in teams if str((c.get("team") or {}).get("id")) == str(team_id)), None)
        other = next((c for c in teams if str((c.get("team") or {}).get("id")) != str(team_id)), None)
        if not ours or not other:
            continue
        try:
            scored, allowed = float(ours["score"]), float(other["score"])
        except (ValueError, TypeError, KeyError):
            continue
        completed.append({
            "Fecha": game.get("date", "")[:10],
            "Rival": (other.get("team") or {}).get("displayName", "N/D"),
            "Local/Visita": "Local" if ours.get("homeAway") == "home" else "Visita",
            "Favor": scored,
            "Contra": allowed,
            "Resultado": "W" if scored > allowed else "L" if scored < allowed else "T"
        })
    completed.sort(key=lambda row: row["Fecha"], reverse=True)
    return completed[:limit]

with t9:
    st.subheader("Team Form & Matchups · NBA / NFL")
    st.caption("Compara resultados finales previos a la fecha del partido. Datos descriptivos; NO predicciones ni picks.")
    if league not in ("NBA", "NFL"):
        st.info("Selecciona NBA o NFL en el menú superior.")
    else:
        form_day = st.date_input("Fecha de la jornada", value=date.today(), key="form_day")
        history_days = st.select_slider("Días anteriores para revisar", options=[7, 14, 21, 30], value=14)
        last_n = st.slider("Últimos partidos completados por equipo", 3, 10, 5)
        st.caption("Se consultan días anteriores únicamente; se excluyen los resultados del día seleccionado para evitar información futura.")
        if st.button("📈 Analizar forma de todos los enfrentamientos", type="primary", key="team_form_run"):
            sport_key, slug = LEAGUES[league]
            try:
                schedule = get_full_scoreboard(sport_key, slug, form_day)
                if not schedule:
                    st.info("No se encontraron partidos para esta fecha.")
                else:
                    with st.spinner(f"Consultando {history_days} días de resultados históricos..."):
                        past_games, failures = historical_scoreboards(sport_key, slug, form_day, history_days)
                    if failures:
                        st.warning(f"Fallaron {len(failures)} de {history_days} consultas históricas. Las estadísticas pueden estar incompletas.")
                    if not past_games:
                        st.warning("No se pudieron obtener resultados históricos. No se calcularán comparaciones.")
                    for game in schedule:
                        comp = (game.get("competitions") or [{}])[0]
                        competitors = comp.get("competitors") or []
                        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
                        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
                        if not away or not home:
                            continue
                        ateam = away.get("team") or {}
                        hteam = home.get("team") or {}
                        with st.expander(f"{ateam.get('displayName', 'Visitante')} @ {hteam.get('displayName', 'Local')}"):
                            comparison = []
                            for side, t in (("Visitante", ateam), ("Local", hteam)):
                                records = team_form(past_games, t.get("id"), last_n)
                                wins = sum(r["Resultado"] == "W" for r in records)
                                losses = sum(r["Resultado"] == "L" for r in records)
                                comparison.append({
                                    "Equipo": t.get("displayName", "N/D"),
                                    "Localía": side,
                                    "Partidos disponibles": len(records),
                                    "Victorias": wins,
                                    "Derrotas": losses,
                                    "Puntos a favor / juego": round(sum(r["Favor"] for r in records) / len(records), 1) if records else None,
                                    "Puntos en contra / juego": round(sum(r["Contra"] for r in records) / len(records), 1) if records else None,
                                })
                                if records:
                                    st.markdown(f"**{t.get('displayName', 'Equipo')} — últimos {len(records)} disponibles**")
                                    st.dataframe(pd.DataFrame(records), hide_index=True, use_container_width=True)
                            st.markdown("**Comparación de forma reciente**")
                            st.dataframe(pd.DataFrame(comparison), hide_index=True, use_container_width=True)
                            st.caption("Muestra reducida y calendario desigual: no ajusta fuerza del rival, lesiones, descanso ni cuotas HRB.")
                    st.info("Próxima etapa: datos históricos de jugadores, normalización de mercados y validación retrospectiva de modelos antes de calcular probabilidades.")
            except (requests.RequestException, ValueError, KeyError) as exc:
                st.error(f"No se pudo completar el análisis: {exc}")


# EDGE X: conservative risk checks and auditable performance tools.
# Neither module places bets, predicts outcomes, nor accesses sportsbook credentials.
from statistics import mean


def risk_check(selection_count, games, probs, odds, stake, bankroll):
    findings = []
    if len(set(games)) < len(games):
        findings.append(("ALTO", "Hay varias selecciones del mismo partido: la independencia puede fallar y HRB puede restringir el parlay."))
    if selection_count >= 10:
        findings.append(("ALTO", "Parlay largo: la probabilidad conjunta puede ser muy pequeña incluso con selecciones individuales fuertes."))
    if any(p < 0.4 for p in probs):
        findings.append(("MEDIO", "Hay selecciones con probabilidad manual inferior al 40%."))
    if bankroll > 0 and stake / bankroll > 0.02:
        findings.append(("ALTO", "La apuesta supera el 2% del presupuesto declarado; considera reducir exposición."))
    if bankroll <= 0:
        findings.append(("DATOS", "Sin presupuesto válido no es posible evaluar exposición."))
    if any(o == 0 for o in odds):
        findings.append(("ERROR", "Hay cuotas americanas inválidas (cero)."))
    if not findings:
        findings.append(("INFORMATIVO", "No se activaron estas reglas básicas. Esto NO certifica una apuesta como segura."))
    return findings

with t10:
    st.subheader("EDGE Risk Shield · evaluación previa")
    st.caption("Herramienta preventiva: verifica concentración, cantidad de selecciones y tamaño de apuesta. No evalúa lesiones ni cuotas en vivo.")
    rcount = st.slider("Selecciones a revisar", 2, 20, 4, key="risk_n")
    rbank = st.number_input("Presupuesto total para apuestas ($)", min_value=0.0, value=500.0, step=25.0, key="risk_bank")
    rstake = st.number_input("Monto del parlay ($)", min_value=0.0, value=10.0, step=5.0, key="risk_stake")
    rdata = pd.DataFrame([{"Partido (ID distinto por juego)": f"Partido {i+1}", "Probabilidad MANUAL (%)": 60.0, "Cuota americana": -110} for i in range(rcount)])
    rdata = st.data_editor(rdata, hide_index=True, num_rows="fixed", use_container_width=True, key=f"risk_editor_{rcount}")
    if st.button("Evaluar riesgos", key="risk_button"):
        try:
            games = [str(x).strip() for x in rdata["Partido (ID distinto por juego)"]]
            probs = [float(x) / 100 for x in rdata["Probabilidad MANUAL (%)"]]
            odds = [int(x) for x in rdata["Cuota americana"]]
            if any(not 0 < x < 1 for x in probs) or any(not x for x in games):
                raise ValueError("Completa partidos y probabilidades válidas entre 0% y 100%.")
            if any(x == 0 for x in odds): raise ValueError("Las cuotas americanas no pueden ser cero.")
            combined_p = math.prod(probs)
            combined_decimal = math.prod(dec(o) for o in odds)
            theoretical_ev = combined_p * combined_decimal - 1
            x,y,z = st.columns(3)
            x.metric("Probabilidad conjunta*", f"{combined_p:.3%}")
            y.metric("Valor esperado / $100*", f"${theoretical_ev*100:+.2f}")
            z.metric("Exposición", f"{rstake/rbank:.1%}" if rbank else "N/D")
            for severity, message in risk_check(rcount, games, probs, odds, rstake, rbank):
                if severity in ("ALTO", "ERROR"): st.error(f"{severity}: {message}")
                elif severity == "MEDIO": st.warning(f"{severity}: {message}")
                else: st.info(f"{severity}: {message}")
            st.caption("*Probabilidades MANUALES y supuesto de independencia. No son probabilidades calibradas ni cuotas verificadas de HRB.")
        except (ValueError, TypeError) as ex:
            st.error(f"Revisa los datos: {ex}")

with t11:
    st.subheader("EDGE Performance Lab · auditoría de resultados")
    st.caption("Importa un CSV con fecha,deporte,partido,mercado,seleccion,cuota,stake,resultado. El archivo se procesa en la sesión; no es un almacenamiento permanente.")
    uploaded = st.file_uploader("Importar historial CSV", type=["csv"], key="performance_csv")
    if uploaded is not None:
        try:
            if uploaded.size > 2_000_000:
                raise ValueError("Archivo demasiado grande (máximo 2 MB).")
            history = pd.read_csv(uploaded)
            needed = {"fecha", "deporte", "partido", "mercado", "seleccion", "cuota", "stake", "resultado"}
            if not needed.issubset(history.columns):
                raise ValueError("Faltan columnas requeridas: " + ", ".join(sorted(needed - set(history.columns))))
            if len(history) > 20000:
                raise ValueError("Máximo 20,000 registros por archivo.")
            history = history.copy()
            history["stake"] = pd.to_numeric(history["stake"], errors="coerce")
            history["cuota"] = pd.to_numeric(history["cuota"], errors="coerce")
            valid = history["resultado"].isin(["Ganada", "Perdida"]) & history["stake"].gt(0) & history["cuota"].notna() & history["cuota"].ne(0)
            settled = history.loc[valid].copy()
            if settled.empty:
                st.info("No hay apuestas liquidadas válidas. Usa Ganada o Perdida en resultado.")
            else:
                settled["profit"] = settled.apply(lambda r: payout_profit(int(r["cuota"]), float(r["stake"]), r["resultado"]), axis=1)
                total_staked = float(settled["stake"].sum())
                net = float(settled["profit"].sum())
                win_rate = float((settled["resultado"] == "Ganada").mean())
                a,b,c,d = st.columns(4)
                a.metric("Apuestas liquidadas", len(settled))
                b.metric("Ganancia neta", f"${net:+,.2f}")
                c.metric("ROI histórico", f"{net/total_staked:.2%}" if total_staked else "N/D")
                d.metric("Tasa de acierto", f"{win_rate:.1%}")
                by_sport = settled.groupby("deporte", dropna=False).agg(Apuestas=("profit","size"), Apostado=("stake","sum"), Neto=("profit","sum")).reset_index()
                by_sport["ROI"] = by_sport["Neto"] / by_sport["Apostado"]
                st.dataframe(by_sport, hide_index=True, use_container_width=True)
                settled["fecha_dt"] = pd.to_datetime(settled["fecha"], errors="coerce")
                settled = settled.sort_values("fecha_dt", kind="stable")
                settled["Balance acumulado"] = settled["profit"].cumsum()
                st.line_chart(settled["Balance acumulado"], use_container_width=True)
                st.download_button("Exportar auditoría CSV", data=settled.drop(columns=["fecha_dt"]).to_csv(index=False).encode("utf-8"), file_name="sport_edge_performance_audit.csv", mime="text/csv")
                st.info(f"Registros excluidos por no estar liquidados o ser inválidos: {len(history)-len(settled)}. El ROI pasado no garantiza resultados futuros.")
        except (ValueError, TypeError, pd.errors.ParserError, UnicodeDecodeError) as ex:
            st.error(f"No se pudo procesar el archivo: {ex}")
    else:
        st.info("Exporta tu historial desde Bet Tracker e impórtalo aquí para revisar el rendimiento.")
