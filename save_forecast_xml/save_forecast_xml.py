from __future__ import annotations

import urllib.request
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import glob
import os
import html

@dataclass
class HourlyPoint:
    ts: datetime
    temp_f: Optional[int]
    conditions: str
    
HEADERS = {'User-Agent': 'Jolhid NWS (jolhid@gmail.com)'}
OutputPath = "/out/HourlyForecast_Archive/"
#OutputPath = "\\mitchell\nws\HourlyForecast_Archive\"
OutputHTMLPath = "/mnt/site/forecast.html"

def _parse_iso_datetime(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _first_text(root: ET.Element, xpath: str) -> Optional[str]:
    el = root.find(xpath)
    if el is None or el.text is None:
        return None
    return el.text.strip()


def _dwml_time_layout_map(root: ET.Element) -> Dict[str, List[datetime]]:
    layouts: Dict[str, List[datetime]] = {}

    for tl in root.findall(".//time-layout"):
        key = _first_text(tl, "./layout-key")
        if not key:
            continue

        times: List[datetime] = []
        for st in tl.findall("./start-valid-time"):
            if st.text:
                times.append(_parse_iso_datetime(st.text.strip()))

        if times:
            layouts[key] = times

    return layouts


def _parse_hourly_temps(root: ET.Element) -> Tuple[str, List[Optional[int]]]:
    temp_el = None
    for el in root.findall(".//temperature"):
        if (el.attrib.get("type") or "").strip().lower() == "hourly":
            temp_el = el
            break

    if temp_el is None:
        present_types = sorted(
            {(el.attrib.get("type") or "").strip() for el in root.findall(".//temperature")}
        )
        raise ValueError(
            "Could not find <temperature type='hourly'> in DWML. "
            f"Temperature types present: {present_types}"
        )

    layout_key = temp_el.attrib.get("time-layout")
    if not layout_key:
        raise ValueError("Hourly temperature element missing time-layout attribute.")

    values: List[Optional[int]] = []
    for v in temp_el.findall("./value"):
        nil_attr = v.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}nil")
        if nil_attr == "true":
            values.append(None)
        else:
            txt = (v.text or "").strip()
            values.append(int(txt) if txt else None)

    return layout_key, values


def _conditions_from_weather_conditions_node(wc: ET.Element) -> str:
    nil_attr = wc.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}nil")
    if nil_attr == "true":
        return "none"

    vals = wc.findall("./value")
    if not vals:
        return "none"

    parts: List[str] = []
    for v in vals:
        wtype = (v.attrib.get("weather-type") or "").strip()
        cov = (v.attrib.get("coverage") or "").strip()
        intensity = (v.attrib.get("intensity") or "").strip()

        chunk_bits = [b for b in [cov, intensity, wtype] if b]
        chunk = " ".join(chunk_bits) if chunk_bits else "unknown"
        parts.append(chunk)

    return " and ".join(parts)


def _parse_hourly_conditions(root: ET.Element) -> Tuple[str, List[str]]:
    weather_el = root.find(".//weather")
    if weather_el is None:
        raise ValueError("Could not find <weather> in DWML.")

    layout_key = weather_el.attrib.get("time-layout")
    if not layout_key:
        raise ValueError("Weather element missing time-layout attribute.")

    conditions: List[str] = []
    for wc in weather_el.findall("./weather-conditions"):
        conditions.append(_conditions_from_weather_conditions_node(wc))

    return layout_key, conditions


def parse_dwml_hourly(xml_text: str) -> List[HourlyPoint]:
    root = ET.fromstring(xml_text)

    time_layouts = _dwml_time_layout_map(root)
    t_layout_key, temps = _parse_hourly_temps(root)
    w_layout_key, conds = _parse_hourly_conditions(root)

    if t_layout_key != w_layout_key:
        raise ValueError(
            f"Time layout mismatch: temps={t_layout_key} weather={w_layout_key}"
        )

    times = time_layouts.get(t_layout_key)
    if not times:
        raise ValueError(f"Could not find time-layout definition for key={t_layout_key}")

    n = min(len(times), len(temps), len(conds))

    points: List[HourlyPoint] = []
    for i in range(n):
        points.append(
            HourlyPoint(
                ts=times[i],
                temp_f=temps[i],
                conditions=conds[i],
            )
        )

    return points


def _pick_daily_conditions(condition_list: List[str]) -> str:
    normalized = [c.lower().strip() for c in condition_list if c]
    normalized = [c for c in normalized if c != "none"]

    if any("snow" in c for c in normalized):
        return "Chance Snow"
    if any("rain" in c for c in normalized):
        return "Chance Rain"
    if not normalized:
        return "Calm"

    return Counter(normalized).most_common(1)[0][0]


def daily_forecast_dataframe_from_dwml(xml_text: str) -> pd.DataFrame:
    hourly = parse_dwml_hourly(xml_text)

    by_day: Dict[date, List[HourlyPoint]] = defaultdict(list)
    for p in hourly:
        by_day[p.ts.date()].append(p)

    rows: List[Dict[str, Any]] = []
    for d in sorted(by_day.keys()):
        points = by_day[d]

        temps = [p.temp_f for p in points if p.temp_f is not None]
        low = min(temps) if temps else None
        high = max(temps) if temps else None

        conditions = _pick_daily_conditions([p.conditions for p in points])

        # Format date like: Mon 1/12 (no leading zeros)
        date_str = f"{d.strftime('%a')} {d.month}/{d.day}"

        # Format temperature like: XXF-XXF (Low-High)
        if low is None or high is None:
            temp_str = "NA"
        else:
            temp_str = f"{low}F-{high}F"

        rows.append(
            {
                "Date": date_str,
                "Temperature": temp_str,
                "Conditions": conditions,
            }
        )

    return pd.DataFrame(rows, columns=["Date", "Temperature", "Conditions"])

def forecast_df_to_html_table(df: pd.DataFrame, title: str = "Forecast") -> str:
    """
    Expects df columns: Date, Temperature, Conditions

    Produces HTML matching your example:
      - white text
      - 18px rows, 24px centered title row
      - 3 columns (Date, Temp, Conditions)
      - date col width=85, temp col width=70
    """

    # Exclude the last row
    df = df.iloc[:-1]
    
    lines = []
    lines.append('<table style="color:white;font-size:18px">')
    lines.append("<tr>")
    lines.append(
        f'<td colspan=3 align=center style="color:white;font-size:24px">{html.escape(title)}</td>'
    )
    lines.append("</tr>")

    for _, row in df.iterrows():
        date_str = "" if pd.isna(row["Date"]) else str(row["Date"])
        temp_str = "" if pd.isna(row["Temperature"]) else str(row["Temperature"])
        cond_str = "" if pd.isna(row["Conditions"]) else str(row["Conditions"])

        # Your example temp is like "32-52" (no "F"), so strip it if present
        temp_str = temp_str.replace("F", "")

        lines.append("<tr>")
        lines.append(f"<td width=85>{html.escape(date_str)}</td>")
        lines.append(f"<td width=70>{html.escape(temp_str)}</td>")
        lines.append(f"<td>{html.escape(cond_str)}</td>")
        lines.append("</tr>")

    lines.append("</table>")
    return "\n".join(lines)


def LogToFile(note: str):

    logoutput = datetime.now().strftime("%Y-%m-%d_%H:%M:%S:%f") + "|" + note + "\n"
    print(logoutput, flush=True)
            
def main():

    LogToFile("Starting up...")
    
    while True:

        response = urllib.request.urlopen("https://forecast.weather.gov/MapClick.php?lat=39.0674&lon=-77.0314&FcstType=digitalDWML")
        htmlsource = response.read()
        LogToFile("Forecast xml file read.")

        if 'htmlsource' not in locals():
            LogToFile("xml file is empty!")
        else:
            try:
                currentdatetime = datetime.now().astimezone(ZoneInfo("America/New_York"))
                currentdatetime = currentdatetime.strftime("%Y%m%d_%H")

                outputfilename = OutputPath + "HourlyForecast_" + currentdatetime + ".xml"
                with open(outputfilename, "wb") as file:
                    file.write(htmlsource)
                LogToFile("Forecast xml file written successfully.")
            except:
                LogToFile("Forecast xml file write failed.")

        htmlsource = None

        with open(outputfilename, "r", encoding="ISO-8859-1") as f:
            XML_TEXT = f.read()

        print(f"Loaded XML from: {outputfilename}")
        df = daily_forecast_dataframe_from_dwml(XML_TEXT)
        forecast_html = forecast_df_to_html_table(df)
        print(forecast_html)

        with open(OutputHTMLPath, "w", encoding="utf-8") as f:
            f.write(forecast_html)
        print(f"Exported html forecast to {OutputHTMLPath}.")

        #Sleep for 1 hour
        LogToFile(f"Sleeping for 1 hour.")
        time.sleep(3600)

if __name__ == '__main__':
    main()


