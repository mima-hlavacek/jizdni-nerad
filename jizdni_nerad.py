import streamlit as st
import pandas as pd
import requests
import datetime
from zoneinfo import ZoneInfo
from urllib.parse import unquote

TZ = ZoneInfo("Europe/Prague")

st.set_page_config(page_title="Jízdní neřád")
st.title("Jízdní neřád")

stops_from_url = st.query_params.get_all("zastavka")

stops = st.text_input(
    "Zastávky oddělěné středníkem",
    value=";".join(stops_from_url) or "Divadlo Gong;Ocelářská",
).split(";")

now = datetime.datetime.now(TZ)
now = now - datetime.timedelta(minutes=now.minute % 5, seconds=now.second, microseconds=now.microsecond)

date = st.date_input("Datum odjezdu", value=now.date(), format="DD.MM.YYYY")
time = st.time_input("Čas odjezdu", value=now.time(), step=5*60)

time_from = datetime.datetime.combine(date, time).replace(tzinfo=ZoneInfo("Europe/Prague"))

raw_data = requests.get(
    "https://api.golemio.cz/v2/pid/departureboards",
    params={
        "names": stops,
        "timeFrom": time_from.isoformat(),
        "minutesAfter": "30",
        "limit": "1000",
    },
    headers={
        "X-Access-Token": st.secrets.access_token,
    }
).json()

stop_id_to_name = {
    stop["stop_id"]: unquote(stop["stop_name"])
    for stop in raw_data["stops"]
}

departures = pd.DataFrame.from_records(
    [
        {
            "predicted_departure": datetime.datetime.fromisoformat(departure["departure_timestamp"]["predicted"]),
            "stop": stop_id_to_name[departure["stop"]["id"]],
            "route": unquote(departure["route"]["short_name"]),
            "headsign": unquote(departure["trip"]["headsign"]),
            "scheduled_departure": datetime.datetime.fromisoformat(departure["departure_timestamp"]["scheduled"]),
            "last_stop": departure["last_stop"]["name"],
            "platform": unquote(departure["stop"]["platform_code"]),
        }
        for departure in raw_data["departures"]
    ]
)
departures["time_until_departure"] = departures["predicted_departure"] - time_from

columns = {
    "predicted_departure": st.column_config.DatetimeColumn("Čas odjezdu", timezone="Europe/Prague", format="HH:mm:ss"),
    "time_until_departure": st.column_config.Column("Doba do odjezdu"),
    "stop": st.column_config.TextColumn("Zastávka"),
    "route": st.column_config.TextColumn("Linka"),
    "headsign": st.column_config.TextColumn("Směr"),
    "scheduled_departure": st.column_config.DatetimeColumn("Čas odjezdu dle jízdního řádu", timezone="Europe/Prague", format="HH:mm:ss"),
    "last_stop": st.column_config.TextColumn("Naposledy na zastávce"),
    "platform": st.column_config.TextColumn("Nástupiště"),
}

st.dataframe(
    departures,
    column_config=columns,
    column_order=list(columns.keys()),
    hide_index=True,
)
