import urllib.request
import time
import datetime
import sys
import os
import hashlib
import glob

images = ["https://radar.weather.gov/ridge/standard/CONUS_0.gif","https://radar.weather.gov/ridge/standard/CONUS-LARGE_0.gif","https://radar.weather.gov/ridge/standard/KLWX_0.gif","https://cdn.star.nesdis.noaa.gov/GOES16/ABI/CONUS/GEOCOLOR/2500x1500.jpg","https://cdn.star.nesdis.noaa.gov/GOES16/ABI/CONUS/Sandwich/2500x1500.jpg"]

imageFileNames = ["CONUS_0","CONUS-LARGE_0","KLWX_0","GEOCOLOR","Sandwich"]

OutputPath = "/mnt/site/image_history/"
#OutputPath = "f:\\tempnws\\image_history\\"

def LogToFile(note: str):

    logoutput = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S:%f") + "|" + note + "\n"
    print(logoutput, flush=True)
    with open(OutputPath + "ExLog.txt", "a") as file:
        file.write(logoutput)
        
def RetrieveFile(image: str, imagefilename: str):

    LogToFile("Retrieving file " + image)

    currentdatetime = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    
    OutputFileName = OutputPath + imagefilename + currentdatetime + image[image.rfind("."):len(image)]
    TempOutputFileName = OutputPath + "Temp_" + imagefilename + currentdatetime + image[image.rfind("."):len(image)]

    urllib.request.urlretrieve(image, f"{TempOutputFileName}")

    LatestFileName = sorted(glob.glob(os.path.join(OutputPath, f"{imagefilename}*.*")), key=os.path.getmtime)[-1]
    PenultimateFileName = sorted(glob.glob(os.path.join(OutputPath, f"{imagefilename}*.*")), key=os.path.getmtime)[-2]

    oldhash = FileHash(f"{LatestFileName}")
    olderhash = FileHash(f"{PenultimateFileName}")
    newhash = FileHash(f"{TempOutputFileName}")

    if oldhash != newhash and olderhash != newhash:
        os.replace(TempOutputFileName, OutputFileName)
        LogToFile(f"Writing file {OutputFileName}.")
    else:
        LogToFile(f"Not a new file {TempOutputFileName}.")

    if os.path.exists(TempOutputFileName):
        os.remove(TempOutputFileName)

def FileHash(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()

def DeleteOldFiles():

    cutofftime = time.time() - (3*24*60*60) # 3 days in seconds
    LogToFile(f"Deleting files before {cutofftime}...")

    for filename in os.listdir(OutputPath):
        filepath = os.path.join(OutputPath, filename)

        if os.path.isfile(filepath):
            if os.path.getmtime(filepath) < cutofftime:
                LogToFile(f"Deleted {filepath}.")
                os.remove(filepath)

def main():

    LogToFile("Starting up...")

    while True:

        for image in images:

            RetrieveFile(image, imageFileNames[images.index(image)])

        DeleteOldFiles()

        LogToFile("Processing complete. Sleeping for 1 minute.")
        time.sleep(60)

if __name__ == "__main__":
    main()

