import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg
import os
import math

HEADERS = {'User-Agent': 'Jolhid NWS (jolhid@gmail.com)'}
OutputPath = "/mnt/site/currcond.html"
DB_USER = os.getenv("NWS_USER")
DB_PASSWORD = os.getenv("NWS_PWD")
DB_PORT = os.getenv("NWS_PORT")
DB_NAME = os.getenv("NWS_DB")

#OutputPath = "f:\\tempnws\\currcond.html"

def LogToFile(note: str):

    logoutput = datetime.now().strftime("%Y-%m-%d_%H:%M:%S:%f") + "|" + note + "\n"
    print(logoutput, flush=True)

def isnumber(value: str):

    if value is None:
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False
        
def get_latest_obs(station_id):
    url = f'https://api.weather.gov/stations/{station_id}/observations/latest'
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    props = resp.json()['properties']
    return {
        'timeStamp':       props.get('timestamp'),                         # ISO8601 str
        'temperature':     props.get('temperature', {}).get('value'),      # °C
        'dewPoint':        props.get('dewpoint', {}).get('value'),      # °C
        'windSpeed':       props.get('windSpeed', {}).get('value'),        # m/s
        'windGust':        props.get('windGust', {}).get('value'),        # m/s
        'windDir':         props.get('windDirection', {}).get('value'),    # degrees
        'humidity':        props.get('relativeHumidity', {}).get('value'),  # %
        'pressure':        props.get('barometricPressure', {}).get('value'),# Pa
        'precipLastHour':  props.get('precipitationLastHour', {}).get('value'),       # meters
        'windChill':       props.get('windChill', {}).get('value'),       # meters
        'heatIndex':       props.get('heatIndex', {}).get('value'),       # meters
        'visibility':      props.get('visibility', {}).get('value'),       # meters
        'description':     props.get('textDescription')                    # e.g. "Mostly Cloudy"
    }

def insert_observation(data, station):

    LogToFile(f"Writing observation for {station} to database...")

    conn = psycopg.connect(
            host="db",
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
    )

    with conn.cursor() as cur:
        cur.execute("""
            insert into public.dat_conditionhistory (location_code, log_date, tempc, dewpoint, windspeed, windgust, winddir, humidity, pressure, preciplasthour, windchill, heatindex, visibility, description)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (location_code, log_date) do nothing;
        """, (
            station,
            data["timeStamp"],
            data["temperature"],
            data["dewPoint"],
            data["windSpeed"],
            data["windGust"],
            data["windDir"],
            data["humidity"],
            data["pressure"],
            data["precipLastHour"],
            data["windChill"],
            data["heatIndex"],
            data["visibility"],
            data["description"],
        ))
            
    conn.commit()
    conn.close()

    LogToFile(f"Observation for {station} inserted successfully.")

def update_current_conditions_web(data):

    if data['temperature'] is None:
        tempF = "NA"
    else:
        tempF = math.floor((data['temperature'] * (9/5)) + 32)
    
    if data['windSpeed'] is None:
        wind = "Calm"
    else:
        wind = f"{round(data['windSpeed'] * 0.621, 0)} @ {data['windDir']}"
        
    if data['windGust'] is None:
        windGustMPH = ""
    else:
        windGustMPH = round(data['windGust'] * 0.621, 0)
        windGustMPH = f"G{round(windGustMPH,0)}"
        
    if isnumber(data['windChill']):
        feelsLike = math.floor((data['windChill'] * (9/5)) + 32, 0)
    elif isnumber(data['heatIndex']):
        feelsLike = math.floor((data['heatIndex'] * (9/5)) + 32, 0)
    else:
        feelsLike = tempF
        
    if data['precipLastHour'] is None:
        precip = "0.00"
    else:
        precip = data['precipLastHour']
        
    if data['dewPoint'] is None:
        dewPoint = "--"
    else:
        dewPoint = round((data['dewPoint'] * (9/5)) + 32, 0)
        
    lastupdate = datetime.fromisoformat(data['timeStamp'])
    lastupdate = lastupdate.astimezone(ZoneInfo("America/New_York"))

    htmlstring = "<table cellspacing=5>\n<tr>\n<td style='color:white;font-size:24px'>\n" \
                 f"{data['description']}<br>{tempF}&deg;F<br>\n" \
                 "</td>\n<td style='color:white;font-size:14px'>\n" \
                 f"Wind {wind}{windGustMPH}<br>\n" \
                 f"Feels Like {feelsLike}&deg;F<br>\n" \
                 f"Dew point {dewPoint}&deg;F Precip last hour {precip}in.<br>\n" \
                 f"as of {lastupdate}\n" \
                 "</td>\n</tr>\n</table>\n"

    with open(OutputPath, "w") as file:
        file.write(htmlstring)
    
def main():

    LogToFile("Starting up...")
    
    # Populate stations
    locations = ["KGAI","KBWI","KNAK","KDMH","KFDK","KIAD","KDCA","KCGS"]

    while True:
        LogToFile(f"Gathering observations...")

        for location in locations:
          
            # Fetch the data
            obs = get_latest_obs(location)

            # Insert into the table (Delete any other records for this station at this time first)
            insert_observation(obs, location)
            if location == "KCGS":
                LogToFile(f"Writing KCGS observation to web...")
                update_current_conditions_web(obs)

        #Sleep for 5 minutes
        LogToFile(f"Sleeping for 5 minutes.")
        time.sleep(300)
        


if __name__ == '__main__':
    main()


