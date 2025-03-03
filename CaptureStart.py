from PIL import ImageGrab
import numpy as np
import cv2
from skimage.metrics import structural_similarity as Ssim
# def ImportModels(): #makes inital startup a lot faster
#     if ModelLoded == False:
#         ModelLoded = True
print("Loading Model....")
from Components.Memory import AddToMemory, GetMemory, ClipMode, RetriveMemoryMax
print("Model loaded")
from Components.Crypt import EncryptDecryptImage 
import time
import os
import threading

def TimeField():
    return time.strftime("%y%m%d%H%M%S")

## Setting for a lot of images when there is a change

global Threshold 
Threshold = 0.9 # had 0.85 now, prev 95 Bigger val easy to start save
global ThresholdSave 
ThresholdSave = 0.6 # had 0.75 now smaller value easy to actualy save - prev 85
global ScreenshotInterval
ScreenshotInterval = 2

global ModelLoded
ModelLoded = False

def CaptureMode(key):
    """
    Sets capture parameters based on different modes for specific tasks.
    
    Parameters:
    - key: String representing the capture mode to use
    
    Available modes:
    - "Normal": Default balanced settings
    - "Games" or "Slow": For games or slower-changing content
    - "Remember" or "Fast": Higher sensitivity for capturing more images
    - "Presentation": For capturing slide presentations
    - "Video": For recording key moments in videos
    - "Coding": For tracking changes in code editors
    - "Security": For surveillance with minimal false positives
    - "Timelapse": For creating timelapses with regular intervals
    """
    global Threshold 
    global ThresholdSave 
    global ScreenshotInterval

    mode_descriptions = {
        "Normal": "Balanced settings for everyday use",
        "Games": "Less frequent captures for gaming sessions",
        "Slow": "Less frequent captures for gaming sessions",
        "Remember": "Higher sensitivity to capture more details",
        "Fast": "Higher sensitivity to capture more details",
        "Presentation": "Optimized for slide decks and presentations",
        "Video": "Captures key scenes and transitions in videos",
        "Coding": "Tracks meaningful changes in code editors",
        "Security": "Minimizes false triggers for surveillance",
        "Timelapse": "Regular interval captures regardless of content"
    }
    
    if key == "Normal":
        Threshold = 0.9 
        ThresholdSave = 0.6 
        ScreenshotInterval = 2
    elif key == "Games" or key == "Slow":  # saves less images
        Threshold = 0.75 
        ThresholdSave = 0.55  # Saves only at big movement, but saves 
        ScreenshotInterval = 4
    elif key == "Remember" or key == "Fast":  # saves more images
        Threshold = 0.96
        ThresholdSave = 0.47
        ScreenshotInterval = 2
    elif key == "Presentation":  # optimized for slide changes
        Threshold = 0.85  # Detect slide transitions
        ThresholdSave = 0.7  # Avoid capturing minor animations
        ScreenshotInterval = 3
    elif key == "Video":  # capture key scenes in videos
        Threshold = 0.8  # Catch scene changes
        ThresholdSave = 0.5  # Save significant visual changes
        ScreenshotInterval = 1
    elif key == "Coding":  # for programming sessions
        Threshold = 0.95  # Less sensitive for code changes
        ThresholdSave = 0.85  # Only save meaningful edits
        ScreenshotInterval = 5
    elif key == "Security":  # surveillance with minimal false triggers
        Threshold = 0.98  # Only trigger on obvious movement
        ThresholdSave = 0.9  # Save when change is substantial
        ScreenshotInterval = 1
    elif key == "Timelapse":  # regular interval captures
        Threshold = 0.1  # Almost always trigger
        ThresholdSave = 0.1  # Almost always save
        ScreenshotInterval = 30  # Every 30 seconds
    else:
        Threshold = 0.9 
        ThresholdSave = 0.6 
        ScreenshotInterval = 2
        
    print( "We are now in: " + key + " Mode")


SaveDirectory = 'CapturedData'

# Ensure the save directory exists
if not os.path.exists(SaveDirectory):
    os.makedirs(SaveDirectory)

def GrabScreen():
    """Captures the current screen."""
    return ImageGrab.grab()

def ImageToArray(image):
    """Converts an image to a numpy array."""
    return np.array(image)

def CalculateSsim(img1, img2):
    """Calculates the Structural Similarity Index (SSIM) between two images."""
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    score, _ = Ssim(gray1, gray2, full=True)
    return score


def GetNextFilename(extension='.png'):
    # existing_files = os.listdir(SaveDirectory)
    # screenshot_numbers = [int(f.split('_')[1].split('.')[0]) for f in existing_files if f.startswith('screenshot_') and f.split('_')[1].split('.')[0].isdigit()]
    # if not screenshot_numbers:
    #     return f'screenshot_1{extension}'
    # next_number = max(screenshot_numbers) + 1
    next_number = TimeField()
    return f'Snap-{next_number}{extension}'


def SaveScreenshot(image,SaveDirectory = 'CapturedData'):
    filename = GetNextFilename()
    filepath = os.path.join(SaveDirectory, filename)
    image.save(filepath)
    return filename

def SaveScreenshotJpg(image, SaveDirectory='CapturedData', quality=90):
    if not os.path.exists(SaveDirectory):
        os.makedirs(SaveDirectory)
    filename = GetNextFilename('.jpg')
    filepath = os.path.join(SaveDirectory, filename)
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    image.save(filepath, 'JPEG', quality=quality)
    return filename

def Main(previous_screenshot, key):
        #global previous_screenshot
        global last_capture_time
        time.sleep(ScreenshotInterval)
        current_screenshot = GrabScreen()
        current_array = ImageToArray(current_screenshot)

        similarity_score = CalculateSsim(previous_screenshot, current_array)
        print("Waiting for change")

        if similarity_score < Threshold: 
            print("Detected a change -") 
            previous_screenshot = current_array
            stable_change_period = 3

            while stable_change_period:
                stable_change_period -= 1
                time.sleep(ScreenshotInterval * 0.3)
                current_screenshot = GrabScreen()
                current_array = ImageToArray(current_screenshot)
                similarity_score = CalculateSsim(previous_screenshot, current_array)

                if similarity_score <= ThresholdSave:
                    print("Screen Changed")
                    break
                print("Screen Didn't change")
            else:
                print("Stable for long")
                saved_filename = SaveScreenshotJpg(current_screenshot)

                print(f'Screenshot saved: {saved_filename}')
                AddToMemory(os.path.join(SaveDirectory, saved_filename))
                print("Added To memory")
                previous_screenshot = current_array
                previous_screenshot = current_array
                time.sleep(ScreenshotInterval/2)
                EncryptDecryptImage(os.path.join(SaveDirectory, saved_filename), key)
        return previous_screenshot

global Start
Start = False #
global Key
Key = ""

# def ThreadMain():
#     try:
#         previous_screenshot = ImageToArray(GrabScreen())
#         last_capture_time = time.time()
#         count = 0
#         print("Started")
#         while True:
#             while Start:
#                 count += 1
#                 previous_screenshot = Main(previous_screenshot, key=Key)
#                 if count > 10:
#                     count = 1
#                     Memory , Names,TimeLine = GetMemory()
#                     JsonData.SaveJson("Data.json",Names,Memory, TimeLine)
#                     print("Saved")
#             if Start == False and count > 0:
#                 count = 0
#                 Memory , Names, TimeLine = GetMemory()
#                 JsonData.SaveJson("Data.json",Names,Memory, TimeLine)
#                 print("Saved")
#                 time.sleep(5)
#     except Exception as e:
#         print(e)
#         time.sleep(5)
#         ThreadMain()

# Threaded = threading.Thread(target=ThreadMain)
# #Threaded.start()

def ThreadMain():
    try:
        previous_screenshot = ImageToArray(GrabScreen())
        print("Started")
        while True:
            while Start:
                previous_screenshot = Main(previous_screenshot, key=Key)
                # No need to manually save anything, database handles persistence
                
            if Start == False:
                # Just sleep when not actively capturing
                time.sleep(5)
    except Exception as e:
        print(f"Error in ThreadMain: {e}")
        time.sleep(5)
        ThreadMain()

Threaded = threading.Thread(target=ThreadMain)
# Threaded.start()




if __name__ == "__main__":
    ThreadMain()
