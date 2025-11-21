import urllib.request
import time
import datetime
import sys
import glob
import os
import hashlib
import imageio.v3 as iio
import imageio_ffmpeg

viewdurations = [100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,100,1000]
imagesets = ["KLWX","CONUS-LARGE","GEOCOLOR","Sandwich"]
hashcontrol = ["","","",""]

#OutputPath = "f:\\tempnws\\image_history\\"
#AniOutputPath = "f:\\tempnws\\RadarAndSatImages\\"
OutputPath = "/mnt/site/image_history/"
AniOutputPath = "/mnt/site/RadarAndSatImages/"

def LogToFile(note: str):
    logoutput = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S:%f") + "|" + note + "\n"
    print(logoutput, flush=True)
    with open(AniOutputPath + "log_mp4.txt", "a") as file:
        file.write(logoutput)

def FileHash(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)

    return h.hexdigest()

def BuildAnimation(fileprefix):

    LogToFile(f"Starting {fileprefix}...")

    curimagesetidx = imagesets.index(fileprefix)

    LatestFileName = sorted(glob.glob(os.path.join(OutputPath, f"{fileprefix}*.*")), key=os.path.getmtime)[-1]
    LatestFileHash = FileHash(LatestFileName)
    
    if LatestFileHash != hashcontrol[curimagesetidx]:

        LogToFile("New file...creating new animation...")
        
        FileNames = sorted(glob.glob(os.path.join(OutputPath, f"{fileprefix}*.*")), key=os.path.getmtime)
        FileNamesLatest36 = FileNames[-36:]

        Images = [iio.imread(p) for p in FileNamesLatest36]
        if Images:
            Images.extend([Images[-1]] * 36) # pause on last frame for 36 frames

        OutputPath_mp4 = os.path.join(AniOutputPath, f"{fileprefix}-Last3Hours.mp4")

        try:
            iio.imwrite(
                OutputPath_mp4,
                Images,
                plugin="FFMPEG",             # explicitly use ffmpeg backend
                codec="libx264",             # H.264 video codec
                fps=12,                      # frames per second (tune as desired)
                quality=8,                   # 0–10 (higher = better)
                output_params=[
                    "-movflags", "+faststart",   # allows faster streaming start
                    "-pix_fmt", "yuv420p"        # ensures web/browser compatibility
                ],
            )
            LogToFile(f"{fileprefix}-Last3Hours.mp4 written to disk.")
        except:
            LogToFile("Failed to create animation.")

        hashcontrol[curimagesetidx] = LatestFileHash
    else:
        LogToFile("No new file...not creating new animation.")
            
def main():

    LogToFile("Starting up...")

    # Sleep for 10 seconds to allow images to be retrieved by other script first
    time.sleep(10)

    while True:

        LogToFile("Building animations.")

        for prefix in imagesets:
            BuildAnimation(prefix)

        LogToFile("Processing complete. Sleeping for 1 minute.")
        time.sleep(60)

if __name__ == "__main__":
    main()

