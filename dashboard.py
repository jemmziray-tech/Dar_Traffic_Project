"""Dar Traffic: observations, coverage and explicitly limited analysis."""
from urllib.parse import urlencode
import pandas as pd
import plotly.express as px
import streamlit as st
from config import ROAD_MAP, ROADS
from utils import get_db
from traffic_data import observations, recent, latest, hourly_profile, scenario, FRESH_MINUTES

PAGES = ['Live overview', 'Road history', 'Patterns & coverage', 'Corridor explorer',
         'Forecast readiness', 'What-if lab', 'Data status']
COLOUR = '#54D6B2'


@st.cache_data(ttl=60, show_spinner=False)
def load_live():
    return [d.to_dict() for d in get_db().collection('live_traffic').stream()]


@st.cache_data(ttl=300, show_spinner=False)
def load_history():
    return [d.to_dict() for d in get_db().collection('traffic_history')
            .order_by('timestamp', direction='DESCENDING').limit(5000).stream()]


def read_data(history=False):
    try:
        raw = load_history() if history else load_live()
        return observations(raw), len(raw), None
    except Exception:
        return observations([]), 0, 'The traffic database could not be reached. Try refreshing shortly.'


def shell(index):
    st.set_page_config(page_title=f'{PAGES[index]} · Dar Traffic', page_icon='◈', layout='wide')
    st.markdown('''<style>
    .block-container {max-width:1280px;padding-top:4.5rem;padding-bottom:3rem}
    h1 {font-weight:650!important;letter-spacing:-.045em!important}
    h2,h3 {letter-spacing:-.025em!important}
    [data-testid="stMetricValue"] {font-variant-numeric:tabular-nums}
    [data-testid="stSidebar"] {border-right:1px solid #233445}
    .eyebrow {color:#54D6B2;font-size:.76rem;font-weight:600;letter-spacing:.16em;margin-bottom:.7rem}
    </style>''', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('### ◈ DAR TRAFFIC')
        st.caption('Dar es Salaam · Tanzania')
        st.divider()
        st.caption('WORKSPACE')
        destinations = ['pages/0_Overview.py', 'pages/1_History.py', 'pages/2_Advanced_Analytics.py',
                        'pages/3_Route_Planner.py', 'pages/4_AI_Predictor.py',
                        'pages/5_RL_Simulation.py', 'pages/6_Live_RL_Tracker.py']
        for i, path in enumerate(destinations):
            st.page_link(path, label=PAGES[i])
        st.divider()
        st.caption('Google traffic estimates · EAT (UTC+3)')
        st.caption('Reads: dar-traffic · No collection runs from this dashboard.')
        if st.button('Refresh displayed data', width='stretch'):
            load_live.clear()
            load_history.clear()
            st.rerun()
        st.caption('Refreshing reads stored observations. It does not collect new traffic.')
    st.markdown('<div class="eyebrow">DAR ES SALAAM / TRAFFIC OBSERVATORY</div>', unsafe_allow_html=True)
    st.title(PAGES[index])


def stamp(value):
    return pd.Timestamp(value).tz_convert('Africa/Dar_es_Salaam').strftime('%d %b %Y · %H:%M EAT')


def status(frame, error=None):
    if error:
        st.error(error)
        return
    fresh = recent(frame)
    if frame.empty:
        st.info('No validated observations are available yet. No substitute data is shown.')
    else:
        st.caption(f'Latest observation {stamp(frame.timestamp.max())} · '
                   f'{fresh.road_id.nunique()} of {len(ROADS)} configured corridors within {FRESH_MINUTES} minutes')
        if fresh.empty:
            st.warning('The latest snapshot is stale. Historical records remain available; current conditions are unknown.')
        elif fresh.road_id.nunique() < len(ROADS):
            st.warning('Coverage is partial. Missing or stale corridors are excluded from current summaries.')


def road_picker(frame, key):
    ids = sorted(frame.road_id.unique(), key=lambda x: ROAD_MAP.get(x, x))
    return st.selectbox('Monitored corridor', ids, format_func=lambda x: ROAD_MAP[x], key=key)


def table(frame):
    view = frame.copy()
    view['Observed (EAT)'] = view['timestamp'].map(stamp)
    view = view.rename(columns={'name':'Corridor', 'live_mins':'Traffic time (min)',
            'normal_mins':'Baseline time (min)', 'delay_mins':'Extra delay (min)',
            'distance_km':'Distance (km)', 'speed_kmh':'Est. speed (km/h)', 'weather':'Weather'})
    columns = ['Corridor','Traffic time (min)','Baseline time (min)','Extra delay (min)',
               'Distance (km)','Est. speed (km/h)','Weather','Observed (EAT)']
    st.dataframe(view[columns].round(2), hide_index=True, width='stretch')


def download(frame, filename):
    st.download_button('Download these observations · CSV', frame.to_csv(index=False).encode('utf-8'),
                       file_name=filename, mime='text/csv')


def chart(fig):
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                      font_color='#DCE7EC', margin=dict(l=0,r=12,t=15,b=0),
                      colorway=[COLOUR, '#E8B96D', '#7DABEF'])
    st.plotly_chart(fig, width='stretch', config={'displaylogo':False})


def overview():
    shell(0)
    st.caption('A snapshot of monitored corridors. Every figure below comes from stored traffic estimates.')
    frame, _, error = read_data()
    status(frame, error)
    fresh = latest(recent(frame))
    if error or fresh.empty:
        st.page_link('pages/1_History.py', label='Explore previous observations →')
        return
    st.divider()
    a,b,c,d = st.columns(4)
    a.metric('Fresh corridors', f'{len(fresh)} / {len(ROADS)}')
    b.metric('Median extra delay', f'{fresh.delay_mins.median():.2f} min')
    c.metric('Largest extra delay', f'{fresh.delay_mins.max():.2f} min')
    d.metric('Sum of route delays', f'{fresh.delay_mins.sum():.2f} min')
    st.caption('Extra delay = max(traffic time − provider baseline, 0). The sum counts each monitored corridor once; '
               'corridors can overlap. It is not total city delay or time lost by all travellers.')
    left,right = st.columns([2,1], gap='large')
    ranked = fresh.sort_values('delay_mins', ascending=False)
    with left:
        st.subheader('Where the extra time is')
        chart(px.bar(ranked.head(10).sort_values('delay_mins'), x='delay_mins', y='name',
                     orientation='h', labels={'delay_mins':'Extra delay (minutes)','name':''},
                     color_discrete_sequence=[COLOUR]))
    with right:
        st.subheader('Snapshot notes')
        worst = ranked.iloc[0]
        st.write(f'**{worst["name"]}** has the largest estimated additional delay in this snapshot.')
        st.write(f'{worst.live_mins:.2f} min traffic time · {worst.normal_mins:.2f} min baseline')
        st.caption('A low delay means the estimate is close to the provider baseline. It does not prove roads are empty.')
        st.page_link('pages/3_Route_Planner.py', label='Inspect a corridor →')
    st.subheader('All monitored corridors')
    search = st.text_input('Find a corridor', placeholder='Try Mwenge, Posta or Mandela')
    filtered = ranked[ranked.name.str.contains(search, case=False, regex=False)]
    table(filtered)
    download(filtered, 'dar-traffic-current.csv')
    with st.expander('How to interpret this page'):
        st.write('Google Distance Matrix provides estimated travel time with traffic, a baseline travel time, and route distance. '
                 'These are estimates for configured endpoint pairs, not physical sensor measurements. '
                 'We exclude invalid records and observations older than 90 minutes from current summaries. '
                 'No economic loss or city efficiency score is inferred.')


def history():
    shell(1)
    st.caption('Inspect the observations behind a corridor. Gaps are left visible.')
    frame, count, error = read_data(True)
    st.caption('History is limited to the latest 5,000 stored records across all corridors.')
    if error:
        st.error(error)
        return
    if frame.empty:
        st.info('There are no validated historical observations yet.')
        return
    road = road_picker(frame, 'history_road')
    selected = frame[frame.road_id == road].copy()
    local_dates = selected.timestamp.dt.tz_convert('Africa/Dar_es_Salaam').dt.date
    bounds = st.date_input('Date range (EAT)', value=(local_dates.min(),local_dates.max()),
                           min_value=local_dates.min(), max_value=local_dates.max())
    if len(bounds) != 2:
        st.info('Choose both a start and an end date.')
        return
    selected = selected[local_dates.between(bounds[0],bounds[1])]
    if selected.empty:
        st.info('No observations fall in this date range.')
        return
    a,b,c = st.columns(3)
    a.metric('Observations', len(selected))
    b.metric('Median extra delay', f'{selected.delay_mins.median():.2f} min')
    c.metric('Most recent', selected.timestamp.max().tz_convert('Africa/Dar_es_Salaam').strftime('%H:%M EAT'))
    if len(selected) < 2:
        st.info('One observation is a snapshot, not a trend. More collections are needed for a time series.')
    else:
        plot = selected.copy()
        plot['Time (EAT)'] = plot.timestamp.dt.tz_convert('Africa/Dar_es_Salaam')
        plot = plot.rename(columns={'live_mins':'Traffic time', 'normal_mins':'Baseline time'})
        chart(px.scatter(plot, x='Time (EAT)', y=['Traffic time','Baseline time'],
                         labels={'value':'Travel time (minutes)','variable':'Estimate'},
                         color_discrete_sequence=[COLOUR,'#7DABEF']))
        st.caption('Traffic time and baseline are plotted as individual observations; no data is invented between them.')
    table(selected.sort_values('timestamp', ascending=False))
    download(selected, f'dar-traffic-{road}-history.csv')


def analytics():
    shell(2)
    st.caption('Describe the sample first. Compare patterns only where observations exist.')
    frame, count, error = read_data(True)
    if error:
        st.error(error)
        return
    if frame.empty:
        st.info('Patterns need validated historical observations. None are available yet.')
        return
    dates = frame.timestamp.dt.tz_convert('Africa/Dar_es_Salaam').dt.date
    a,b,c = st.columns(3)
    a.metric('Validated observations', len(frame))
    b.metric('Observed calendar days', dates.nunique())
    c.metric('Corridors represented', f'{frame.road_id.nunique()} / {len(ROADS)}')
    st.caption(f'Window: {stamp(frame.timestamp.min())} to {stamp(frame.timestamp.max())}. Latest 5,000 records only.')
    if dates.nunique() < 7:
        st.warning('Less than seven observed days. This sample cannot establish a reliable weekly traffic pattern.')
    road = road_picker(frame, 'pattern_road')
    selected = frame[frame.road_id == road]
    profile = hourly_profile(selected)
    st.subheader('Observed delay by hour')
    st.dataframe(profile.round(2), hide_index=True, width='stretch')
    st.caption('An absent hour means no observations. A zero means delay was estimated at zero. These are different.')
    st.subheader('Collection coverage')
    coverage = frame.assign(day=dates).groupby(['name','day']).size().reset_index(name='Observations')
    chart(px.scatter(coverage, x='day', y='name', size='Observations',
                     labels={'day':'Date (EAT)','name':'Corridor'}, color_discrete_sequence=[COLOUR]))
    download(frame, 'dar-traffic-validated-history.csv')


def corridors():
    shell(3)
    st.caption('Inspect one measured endpoint pair. Use Google Maps for complete directions.')
    frame, _, error = read_data()
    status(frame, error)
    road = st.selectbox('Configured corridor', list(ROAD_MAP), format_func=lambda x:ROAD_MAP[x])
    config = next(r for r in ROADS if r['id'] == road)
    a,b = st.columns(2)
    with a:
        st.subheader(ROAD_MAP[road])
        st.caption(f'Start: {config["start"]} · End: {config["end"]}')
        url = 'https://www.google.com/maps/dir/?' + urlencode({'api':1, 'origin':config['start'],
                                                               'destination':config['end'], 'travelmode':'driving'})
        st.link_button('Open directions in Google Maps ↗', url)
    with b:
        chosen = latest(frame[frame.road_id == road])
        if chosen.empty or error:
            st.info('No validated observation is available for this corridor.')
        else:
            row = chosen.iloc[0]
            st.caption(f'Observed {stamp(row.timestamp)}')
            if row.age_mins > FRESH_MINUTES:
                st.warning('Historical snapshot · current travel time is unknown.')
            c,d = st.columns(2)
            c.metric('Estimated traffic time', f'{row.live_mins:.2f} min')
            d.metric('Extra delay', f'{row.delay_mins:.2f} min')
            st.write(f'Provider baseline: {row.normal_mins:.2f} min · Route distance: {row.distance_km:.2f} km')
    st.divider()
    st.subheader('Why this is a corridor explorer')
    st.write('The monitored corridors have different endpoints and some overlap. Adding their times would not produce '
             'a valid door-to-door route. This page therefore shows the actual measured pair and links to directions '
             'rather than claiming a fastest complete journey.')


def forecasts():
    shell(4)
    st.caption('Prediction is a separate capability from displaying current traffic.')
    frame, _, error = read_data(True)
    if error:
        st.error(error)
        return
    days = 0 if frame.empty else frame.timestamp.dt.tz_convert('Africa/Dar_es_Salaam').dt.date.nunique()
    st.info('No validated forecasting model is published for the fresh database. Predicted arrival times are unavailable.')
    a,b = st.columns(2)
    a.metric('Fresh-project training observations', len(frame))
    b.metric('Observed calendar days', days)
    st.caption('Counts cover the latest 5,000 history records, not the entire lifetime of the project.')
    st.subheader('Before a model can be useful')
    st.write('Collect repeated observations across peak and off-peak periods; reserve later dates for evaluation; '
             'compare the model against simple baselines; and publish the error in minutes alongside its coverage. '
             'A row count alone does not demonstrate predictive accuracy.')
    if not frame.empty:
        road = road_picker(frame, 'forecast_road')
        profile = hourly_profile(frame[frame.road_id == road])
        adequate = profile[(profile['Days'] >= 7) & (profile['Observations'] >= 14)]
        st.subheader('Historical context, not a forecast')
        if adequate.empty:
            st.caption('No hour has at least 14 observations across seven days for this corridor. No best-departure recommendation is made.')
        else:
            st.dataframe(adequate.round(2), hide_index=True, width='stretch')
            st.caption('These are sampled historical medians for supported hours, not predictions of your next trip.')
    st.page_link('pages/2_Advanced_Analytics.py', label='Review data coverage →')


def scenarios():
    shell(5)
    st.caption('An arithmetic sandbox. Explore an assumption without presenting it as a measured improvement.')
    frame, _, error = read_data()
    fresh = latest(recent(frame))
    if error:
        st.warning(error)
    source = st.radio('Starting point', ['Enter a hypothetical trip', 'Use a recent corridor observation'])
    if source == 'Use a recent corridor observation':
        if fresh.empty:
            st.info('No recent corridor observations are available. Choose a hypothetical trip instead.')
            return
        road = road_picker(fresh, 'scenario_road')
        row = fresh[fresh.road_id == road].iloc[0]
        travel, baseline = row.live_mins, row.normal_mins
        st.caption(f'{stamp(row.timestamp)} · Traffic {travel:.2f} min · Baseline {baseline:.2f} min')
    else:
        a,b = st.columns(2)
        baseline = a.number_input('Baseline travel time (minutes)', min_value=0.1, max_value=600.0, value=20.0, step=1.0)
        extra = b.number_input('Additional delay (minutes)', min_value=0.0, max_value=600.0, value=10.0, step=1.0)
        travel = baseline + extra
    reduction = st.slider('Assumed reduction in additional delay (%)', 0, 100, 20)
    after,saved = scenario(travel, baseline, reduction)
    a,b,c = st.columns(3)
    a.metric('Starting travel time', f'{travel:.2f} min')
    b.metric('Scenario travel time', f'{after:.2f} min')
    c.metric('Hypothetical time saved', f'{saved:.2f} min')
    st.caption('Scenario time = starting time − max(starting time − baseline, 0) × assumed reduction. '
               'This is not a trained reinforcement-learning policy or evidence that an intervention achieves these savings.')
    chart(px.bar(pd.DataFrame({'Case':['Starting point','Your scenario'], 'Minutes':[travel,after]}),
                 x='Case', y='Minutes', color_discrete_sequence=[COLOUR]))


def data_status():
    shell(6)
    st.caption('See what is available, what is excluded, and where the limits are.')
    frame, count, error = read_data()
    status(frame, error)
    a,b,c = st.columns(3)
    a.metric('Stored latest records read', count)
    b.metric('Validated records', len(frame))
    c.metric('Fresh corridors', recent(frame).road_id.nunique())
    st.subheader('Corridor coverage')
    coverage = pd.DataFrame({'road_id':list(ROAD_MAP),'Corridor':list(ROAD_MAP.values())})
    available = latest(frame)[['road_id','timestamp','age_mins']]
    coverage = coverage.merge(available, on='road_id', how='left')
    coverage['State'] = coverage.age_mins.map(lambda age:'Missing' if pd.isna(age) else ('Recent' if age <= FRESH_MINUTES else 'Stale'))
    coverage['Last observation (EAT)'] = coverage.timestamp.map(lambda t:'—' if pd.isna(t) else stamp(t))
    st.dataframe(coverage[['Corridor','State','Last observation (EAT)']], hide_index=True, width='stretch')
    st.subheader('Data contract')
    st.write('Source: Google Distance Matrix traffic estimates. Storage: dar-traffic. '
             'Only schema version 2, traffic-aware, finite positive duration/distance records for configured roads are accepted. '
             'Timestamps in the future are excluded. Current summaries use observations no older than 90 minutes.')
    st.write('Weather is contextual and does not multiply traffic estimates. Client access is read-only. '
             'No personal journey traces, vehicle counts or measured economic losses are available.')
    st.subheader('Collection and model controls')
    st.write('This dashboard cannot start collection, change schedules or publish models. '
             'Check GitHub Actions for the actual collector status. A recent record alone does not prove that recurring collection is enabled.')
    st.link_button('View collector runs ↗', 'https://github.com/jemmziray-tech/Dar_Traffic_Project/actions/workflows/traffic_scraper.yml')
    st.caption('Public traffic reads may incur Firestore read charges. History queries are bounded to 5,000 records and cached for five minutes.')
