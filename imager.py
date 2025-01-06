import time
from picamera2 import Picamera2
import numpy as np
import csv
import json
import os
from filter_curves import filter
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
import base64
from io import BytesIO

font_path = "/home/pi/magi/fonts"

LED_PIN = 13    # status LED - value must be the same as in magi_server.py
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT) 

# Image size:
w = 640         # min of 64, max of 2592 for 5MP camera
h = int(3*w/4)  # native 4:3 aspect ratio
res = (w,h)  

cam = Picamera2() 

#data_directory = 'data'
data_directory = '/path/to/ramdisk'

# Set up list containing upper left corner of all ROIs:
well_cols = 4   # number of well columns
well_rows = 3   # number of well rows
roi_upper_left = (200,185)   # cordinates for upper left corner of upper left ROI
roi_spacing = 62     # spacing (x & y) between ROI centers
roi_width = 12
roi_height = 28 
ROIs = []            # list of upper left corners for all ROIs
for i in range(well_rows):
    for j in range(well_cols):
        x = roi_upper_left[0] + roi_spacing*j
        y = roi_upper_left[1] + roi_spacing*i
        ROIs.append((x,y))

def hex_to_rgb(h):   # convert "#rrggbb" to [R,G,B]
    return [int(h[i:i+2], 16) for i in (1, 3, 5)]

def add_ROIs(img, data):      # Add ROIs to a captured image
    try:
        # Extract well names & colors:
        card_filename = data[0]       # user-selected card file name
        well_config = data[1]        # well configuration
        target_dict = data[2]        # target colors
        colors = [target_dict[t][0] for t in well_config]
        img = img.convert('RGBA')   # convert captured image to support an alpha channel
        img_roi = Image.new('RGBA', img.size, (255, 255, 255, 0))  # create new image with ROIs only
        draw = ImageDraw.Draw(img_roi)
        for idx,roi in enumerate(ROIs):
            roi_lower_right = (roi[0] + roi_width, roi[1] + roi_height)
            fill_color = hex_to_rgb(colors[idx])  # convert "#rrggbb" to [R,G,B]
            fill_color.append(64)  # Add alpha channel for transparency
            draw.rectangle([roi, roi_lower_right], outline='#ffffff', fill=tuple(fill_color))   # Draw ROI
            font = ImageFont.truetype(font_path + "/" + "OpenSans.ttf", 9)         # Add well target text
            text_position = (roi[0] + roi_width + 1, roi[1])
            draw.text(text_position, well_config[idx],'#ffffff',font=font)
        font_timestamp = ImageFont.truetype(font_path + "/" + "OpenSans.ttf", 12) 
        draw.text((10,10), card_filename, font=font_timestamp)  
        draw.text((10,20), time.strftime("%Y%m%d_%Hh%Mm%Ss"), font=font_timestamp)
        img_new = Image.alpha_composite(img, img_roi)  # composite captured & ROI images
        return(img_new)
    except Exception as e:
        print('Exception in get_image():', flush=True)
        print(f'{type(e)}: {e}', flush=True)

def adjust_settings(exposure_time_ms, analogue_gain, color_gains):
    try:
        print("adjust_settings() called with", flush=True)
        print(f"exposure_time={int(exposure_time_ms*1e3)} us", flush=True)
        print(f"analogue_gain={float(analogue_gain)}", flush=True)
        print(f"color_gains={color_gains}", flush=True)
        cam.set_controls({
            "AeEnable": False,                 # auto update of gain & exposure settings
            "AwbEnable": False,                # auto white balance
            "ExposureTime": int(exposure_time_ms*1e3),   # units of microseconds
            "AnalogueGain": float(analogue_gain),   # range [0,6.0] ?
            "ColourGains": color_gains              # (red,blue) gains, range [0,32.0]
        })
        time.sleep(3)   # time to stabilize settings
        return('adjust_settings() done')
    except Exception as e:
        print(f'error in adjust_settings(): {e}', flush=True)
        return('error in adjust_settings()')

def setup_camera(exposure_time_ms=50, analogue_gain=0.5, color_gains=(1.2,1.0)):    # Set up camera
    config = cam.create_still_configuration(main={"size": res})
    cam.configure(config)
    adjust_settings(exposure_time_ms, analogue_gain, color_gains)
    print('Picamera2 setup complete', flush=True)
    os.makedirs(data_directory, exist_ok=True)

def roi_avg(image, roi):   # Return average pixel values in ROI
    r,b,g = 0,0,0
    px,py = roi
    for x in range(int(px),int(px+roi_width)):
        for y in range(int(py),int(py+roi_height)):
            xy = (x,y)
            r += image.getpixel(xy)[0]
            g += image.getpixel(xy)[1]
            b += image.getpixel(xy)[2]
    pixels = roi_width * roi_height;
    r = int(100*r/pixels);
    g = int(100*g/pixels);
    b = int(100*b/pixels);
    return((r,g,b))

def get_image_data():    # Extract fluorescence measurements from ROIs in image
    try:
        cam.start()
        GPIO.output(LED_PIN, GPIO.LOW)     # Turn off LED
        image = cam.capture_image("main")   # capture as PIL image
        cam.stop()
        GPIO.output(LED_PIN, GPIO.HIGH)      # Turn on LED
        # Get average pixel value for each ROI:
        roi_avgs = []
        for roi in ROIs: 
            roi_avgs.append(roi_avg(image, roi)[1])  # green channel
        # Add timestamp & ROI averages to temp data file:
        timestamp = [int(time.time())]        # 1st entry is the time stamp
        with open(data_directory + '/temp_data.csv', 'a') as f:
            writer = csv.writer(f, delimiter=',', lineterminator='\n')
            writer.writerow(timestamp + roi_avgs)
        return(roi_avgs)
    except Exception as e:
        print(f'Exception in get_image_data(): {e}', flush=True)

def get_image(data):       # Return a PIL image with colored ROI boxes for display
    # data structure: [cardFilename, wellConfig, target_dict]
    try:
        cam.start()
        GPIO.output(LED_PIN, GPIO.LOW)
        image = cam.capture_image("main")   # capture as PIL image
        cam.stop()
        GPIO.output(LED_PIN, GPIO.HIGH)
        # Add ROIs to image only if the well configuration has been defined:
        well_config = data[1]
        if len(well_config)>0:   # make sure JS wellConfig is defined
            image = add_ROIs(image, data) 
        buffer = BytesIO()                   # create a buffer to hold the image
        image.save(buffer, format="PNG") # Convert image to PNG
        png_image = buffer.getvalue()
        png_base64 = base64.b64encode(png_image).decode('utf-8')  # Encode as base64
        return(f"data:image/png;base64,{png_base64}")
    except Exception as e:
        print(f'Exception in get_image(): {e}', flush=True)

# Delete contents of the temp data file:
def clear_temp_file():
    with open(data_directory + '/temp_data.csv', 'w') as f:
        pass     

def end_imaging():
    # move temp data contents to time-stamped file:
    output_filename = time.strftime("%Y%m%d_%Hh%Mm%Ss")
    os.rename(data_directory + '/temp_data.csv', data_directory + '/' + output_filename + '.csv')
    clear_temp_file()
    return(output_filename)

def analyze_data(filename, filter_factor, cut_time, threshold):
    # filter() returns format: [ttp, y_filtered_dict]
    # where ttp is a list of TTP values for each well, and
    # y_filtered_dict is a list of data with format:
    #   [ [{x: t1, y: val1}, {x: t2, y: val2}, ...]  <- well 1
    #     [{x: t1, y: val1}, {x: t2, y: val2}, ...]  <- well 2
    #      ... ]                                     <- etc
    results = filter(data_directory + '/' + filename + '.csv', float(filter_factor), float(cut_time), int(threshold)) 

    # Save filtered data to csv file:
    data = results[1]
    time_in_min = [entry['x'] for entry in data[0]]  # time values (same for all wells)
    columns = []
    for well_data in data:
        columns.append([entry["y"] for entry in well_data])
    with open(data_directory + '/' + filename + '_filt.csv', 'a') as f:
        #fieldnames = ["time (min)", "fluorescence"]
        writer = csv.writer(f)
        headers = ["time (min)"] + [f"well {i}" for i in range(len(columns))]
        writer.writerow(headers)
        for i, t in enumerate(time_in_min):
            row = [t] + [values[i] for values in columns]
            writer.writerow(row)

    # Return original list of dicts:
    return(results)

