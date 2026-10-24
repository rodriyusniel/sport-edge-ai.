import csv
import io
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title='SPORT EDGE AI · v0.3', page_icon='📈', layout='wide')
st.title('SPORT EDGE AI')
st.caption('v0.3 · Herramienta privada de análisis · Sin apuestas automáticas ni probabilidades predictivas')
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
        rows.append({'Inicio (UTC)':ev.get('date',''), 'Visitante':away.get('team',{}).get('displayName',''), 'Local':home.get('team',{}).get('displayName',''), 'Estado':ev.get('status',{}).get('type',{}).get('description',''), 'Marcador':f"{away.get('score','–')} - {home.get('score','–')}"})
    return rows

league=st.selectbox('Deporte',list(LEAGUES))
soccer_slug = None
if league == 'Soccer':
    soccer_competition = st.selectbox('Competición de fútbol', list(SOCCER_LEAGUES))
    soccer_slug = SOCCER_LEAGUES[soccer_competition]
t1,t2,t3,t4=st.tabs(['📅 Sports Dashboard','📊 Betting Analyzer','🧩 Parlay Builder','📒 Bet Tracker'])
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
    st.caption('Introduce cada selección y su cuota. Las probabilidades individuales son manuales.')
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
st.divider()
st.caption('SPORT EDGE AI v0.3 · Sin conexión a HRB, sin apuestas automáticas, sin predicciones calibradas y sin Telegram. Uso informativo.')
