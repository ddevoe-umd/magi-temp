# Multiplexed Array Gene Imager (MAGI) server

from simple_pid import PID   # see https://pypi.org/project/simple-pid/
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
import os
import subprocess
import time
import threading
import RPi.GPIO as GPIO
from gpiozero import MCP3008

import imager
import config   # Cross-module global variables for all Python codes

# import objgraph # temp module for tracking memory leaks

sys.path.append(config.magi_directory)  # Add application path to the Python search path

# PID:
GPIO.setmode(GPIO.BCM)
GPIO.setup(config.STATUS_LED_PIN, GPIO.OUT)     # System status LED pin
GPIO.setup(config.FAN, GPIO.OUT) 
GPIO.setup(config.PWM_PIN, GPIO.OUT) 
pwm = GPIO.PWM(config.PWM_PIN,490)
pid = PID(Kp=12.635, Ki=1.0063, Kd=0, setpoint=0)     # Can add sample_time, output_limits, etc.
pid.output_limits = (0,100)
b_bias = 0.82                   # value for linear interpolation of temperature
well_temp = 0                   # current well temperature
set_temp = 60

# Pre-Filter:
a_val = 0.999949373
b_val = 0.0000506268
r_F_prev = 23.0

# Start heater PWM:
duty_cycle = 0
pwm.start(duty_cycle)

# ADC for temperature sensing:
const = MCP3008(channel=0)
Tb = MCP3008(channel=1)
Tt = MCP3008(channel=2)

# Flag to halt temperature control thread:
stop_event = threading.Event()

class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*');
        self.end_headers()

    # File download requests come as GET requests:
    def do_GET(self):
        if os.path.isfile(self.path):
            print(f'accessing {self.path}', flush=True)
            file_size = os.path.getsize(self.path)
            if self.path.endswith(".csv"):
                content_type = "text/csv"
            else:
                content_type = "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header('Access-Control-Allow-Origin', '*');
            self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(self.path)}"')
            self.send_header("Content-Length", str(file_size))
            self.end_headers()
            with open(self.path, "rb") as file:    
                self.wfile.write(file.read())       # Send the file
        else:
            print(f'File not found (204 = no operation)', flush=True)
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            #self.wfile.write(b"File not found.")

    # Server function requests come as POST requests:
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])  # gets the size of data
        post_data = self.rfile.read(content_length)           # get the data
        self._set_response()
        post_data_decoded = post_data.decode('utf-8')
        post_dict = dict(pair.split('=') for pair in post_data_decoded.split('&'))
        info = json.loads(post_dict['todo'])
        action = info[0]
        data = info[1]
        #print(f'{action}: {data}', flush=True)
        # objgraph.show_most_common_types()  # check memory use
        # sys.stdout.flush()
        if action == 'setupAssay':       # Update global variables from the assay card data
            config.card_filename = data['card_filename']
            card_data = data['card_dict']
            config.well_config = card_data["well_config"]
            config.roi_upper_left = tuple(int(val) for val in card_data["roi_upper_left"])
            config.roi_width = int(card_data["roi_width"])
            config.roi_height = int(card_data["roi_height"])
            config.roi_spacing_x = int(card_data["roi_spacing_x"])
            config.roi_spacing_y = int(card_data["roi_spacing_y"])
            config.positives = card_data["positives"]
            config.target_names = data['target_names']
            config.target_colors = data['target_colors']
            imager.setup_ROIs()      # set up the ROIs from assay card data
            imager.get_image(True)   # capture a new image showing ROIs
            results = "config.py globals updated from card data"
            self.wfile.write(results.encode('utf-8'))
        if action == 'ping':                  # respond to server ping
            results = 'server is ready'
            self.wfile.write(results.encode('utf-8'))
        if action == 'onLoad':                # Housekeeping on starting application
            results = clear_globals()         # clear all global variables
            self.wfile.write(results.encode('utf-8'))
        if action == 'start':    # Start the PID loop for temp control
            clear_temp_file()    # Clear temp data file (if "end assay" not hit last run)
            start_pid()
            results = "PID thread started"
            self.wfile.write(results.encode('utf-8'))
        if action == 'getImage':              # Return an image of the chip with colored ROIs
            add_ROIs = data
            results = imager.get_image(add_ROIs)
            self.wfile.write(results.encode('utf-8'))
        if action == 'getImageData':          # Capture image & ROI values
            results = imager.get_image_data()
            self.wfile.write(",".join([str(x) for x in results]).encode('utf-8'))
        if action == 'getTemperature':        # Return chip temperature
            results = str(well_temp)
            self.wfile.write(results.encode('utf-8'))
        elif action == 'endAssay':                 # Turn off PID loop and rename final data file
            results = imager.end_imaging()
            print('calling end_pid()', flush=True)
            sys.stdout.flush()
            end_pid()
            self.wfile.write(results.encode('utf-8'))
        elif action == 'adjust':              # Turn off PID loop and rename final data file
            exposure_time_ms = int(data['exposure_time'])
            analogue_gain = float(data['analogue_gain'])
            colour_gains = (float(data['red_gain']), float(data['blue_gain']))
            results = imager.adjust_settings(exposure_time_ms, analogue_gain, colour_gains)
            self.wfile.write(results.encode('utf-8'))
        elif action == 'analyze':             # Filter curves & extract TTP values
            filename = data['filename']
            filter_factor = data['filter_factor']
            cut_time = data['cut_time']
            threshold = data['threshold']
            results = imager.analyze_data(filename, filter_factor, cut_time, threshold)
            self.wfile.write(json.dumps(results).encode('utf-8'))
            #self.wfile.write(results.encode('utf-8'))
        elif action == 'shutdown':       # Power down the Pi
            shutdown()
        elif action == 'reboot':         # Reboot the Pi
            reboot()
        elif action == 'getLog':         # Return the server log file contents
            if not os.path.isfile(config.logfile):    # Create a blank file if it doesn't exist
                with open(config.logfile, 'w') as f:
                    pass
            with open(config.logfile, 'r') as f:
                results = f.read()
            results += f"\n\nLog file size: {float(os.path.getsize(config.logfile))/1e6:.02f} MB"
            self.wfile.write(json.dumps(results).encode('utf-8'))
        elif action == 'clearLog':          # Clear the server log file
            open(config.logfile, 'w').close()
            results = f'{config.logfile} cleared'
            print(results, flush=True)
            self.wfile.write(json.dumps(results).encode('utf-8'))

    def log_message(self, format, *args):  # Suppress server output
        return

# Delete contents of the temp data file:
def clear_temp_file():
    with open(config.data_directory + '/temp_data.csv', 'w') as f:
        pass     

# Clear globals in config.py:
def clear_globals():
    config.well_config = []
    config.roi_upper_left = (0,0)   # cordinates for upper left corner of upper left ROI
    config.roi_width = 0            # box size
    config.roi_height = 0 
    config.roi_spacing_x = 0        # spacing between ROI centers
    config.roi_spacing_y = 0        
    config.ROIs = []                # list of upper left corners for all ROIs
    config.card_filename = ''
    config.target_names = []
    config.target_colors = []
    return('globals cleared')


# Calibration function for PWM (temperature control):
def cali_fun(y_data):
    y_adj = (
        0.00000000000225474 * y_data ** 5 -
        0.00000000027648357 * y_data ** 4 -
        0.00000000611604906 * y_data ** 3 +
        0.00005022119088712 * y_data ** 2 +
        0.10392688339191500 * y_data +
        24.8772182731984000
        )
    return y_adj

# Function for Pre-Filter Calculation:
def Gp(des_temp):
    global r_F_prev
    r_F = a_val*r_F_prev + b_val*des_temp
    r_F_prev = r_F
    return r_F

# Temperature control (run in separate thread):
def run_pid(stop_event):
    global well_temp
    global const, Tb, Tt
    rd = 50*1e6       # PID update period (ns)
    ptrd = time.time_ns()
    start_time = time.time_ns()
    while not stop_event.is_set():
        try:
            pid.setpoint = Gp(set_temp)     # Change setpoint based on Pre-Filter
            value_raw = [const.value, Tb.value, Tt.value]    # Read ADC values
            values = [x*1023 for x in value_raw]
            # Change the duty cycle based on the ADC reading    
            duty_cycle = pid(b_bias*cali_fun(values[1] - values[0]) + (1-b_bias)*cali_fun(values[2] - values[0]))
            pwm.ChangeDutyCycle(duty_cycle)
            if time.time_ns() - ptrd >= rd:      # Update values every 50ms
                ptrd = time.time_ns()
                well_temp = b_bias*cali_fun(values[1] - values[0]) + (1-b_bias)*cali_fun(values[2] - values[0])
        except Exception as e:
            print(f'Exception in run_pid: {e}', flush=True)

def start_pid():
    GPIO.output(config.FAN, GPIO.HIGH)   # Turn on system fan
    t = threading.Thread(target=run_pid, args=(stop_event,))    # Start the PID loop
    t.daemon = True
    t.start()

def end_pid():
    print('end_pid() called', flush=True)
    sys.stdout.flush()
    stop_event.set()
    pwm.ChangeDutyCycle(0)

def run(port):
    handler_class=S
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler_class)
    print("MAGI server started", flush=True)
    print("Setting up camera...", flush=True)
    sys.stdout.flush()
    imager.setup_camera(exposure_time_ms=50, analogue_gain=0.5, color_gains=(1.2,1.0))
    print("Camera setup done", flush=True)
    print("System ready", flush=True)
    sys.stdout.flush()
    GPIO.output(config.STATUS_LED_PIN, GPIO.HIGH)  # turn LED on to indicate system is ready
    try:
        httpd.serve_forever()     # blocking call
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    GPIO.cleanup()
    print('\n\nGPIO cleaned up', flush=True)
    sys.stdout.flush()

def shutdown():
    GPIO.cleanup()
    subprocess.call("sudo shutdown -h now", shell=True)

def reboot():
    GPIO.cleanup()
    subprocess.call("sudo reboot", shell=True)


if __name__ == "__main__":
    print("MAGI server starting...", flush=True)
    sys.stdout.flush()
    run(8080)


