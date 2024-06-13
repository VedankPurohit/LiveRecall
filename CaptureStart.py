from PIL import ImageGrab
import numpy as np
import cv2
from skimage.metrics import structural_similarity as Ssim
from Components.Memory import AddToMemory, GetMemory, JsonData, ClipMode, RetriveMemoryMax
from Components.Crypt import EncryptDecryptImage 
import time
import os
import threading

global Threshold 
Threshold = 0.95
global ThresholdSave 
ThresholdSave = 0.85
global ScreenshotInterval
ScreenshotInterval = 2

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

def GetNextFilename():
    existing_files = os.listdir(SaveDirectory)
    screenshot_numbers = [int(f.split('_')[1].split('.')[0]) for f in existing_files if f.startswith('screenshot_') and f.split('_')[1].split('.')[0].isdigit()]
    if not screenshot_numbers:
        return 'screenshot_1.png'
    next_number = max(screenshot_numbers) + 1
    return f'screenshot_{next_number}.png'

def SaveScreenshot(image,SaveDirectory = 'CapturedData'):
    filename = GetNextFilename()
    filepath = os.path.join(SaveDirectory, filename)
    image.save(filepath)
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
                saved_filename = SaveScreenshot(current_screenshot)

                print(f'Screenshot saved: {saved_filename}')
                AddToMemory(os.path.join(SaveDirectory, saved_filename))
                print("Added To memory")
                previous_screenshot = current_array
                previous_screenshot = current_array
                time.sleep(ScreenshotInterval/2)
                EncryptDecryptImage(os.path.join(SaveDirectory, saved_filename), key)
        return previous_screenshot

global Start
Start = False
global Key
Key = ""

def ThreadMain():
    previous_screenshot = ImageToArray(GrabScreen())
    last_capture_time = time.time()
    count = 0
    print("Started")
    while True:
        while Start:
            count += 1
            previous_screenshot = Main(previous_screenshot, key=Key)
            if count > 10:
                count = 1
                Memory , Names = GetMemory()
                JsonData.SaveJson("Data.json",Names,Memory)
                print("Saved")
        if Start == False and count > 0:
            count = 0
            Memory , Names = GetMemory()
            JsonData.SaveJson("Data.json",Names,Memory)
            print("Saved")

Threaded = threading.Thread(target=ThreadMain)
#Threaded.start()




if __name__ == "__main__":
    ThreadMain()
