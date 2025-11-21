import urllib.request
import time
from datetime import datetime
from zoneinfo import ZoneInfo

HEADERS = {'User-Agent': 'Jolhid NWS (jolhid@gmail.com)'}
OutputPath = "/out/HourlyForecast_Archive/"
#OutputPath = "\\mitchell\nws\HourlyForecast_Archive\"

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

        #Sleep for 1 hour
        LogToFile(f"Sleeping for 1 hour.")
        time.sleep(3600)

if __name__ == '__main__':
    main()


