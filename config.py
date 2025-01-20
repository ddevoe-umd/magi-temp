
import os

# Cross-module Python global variables:

well_config = []
roi_upper_left = (0,0)   # cordinates for upper left corner of upper left ROI
roi_width = 0            # box size
roi_height = 0 
roi_spacing_x = 0        # spacing between ROI centers
roi_spacing_y = 0        
ROIs = []                # list of upper left corners for all ROIs

# File information:
magi_directory = os.environ['HOME'] + '/magi'
font_directory = magi_directory + '/fonts'
data_directory = '/path/to/ramdisk'
card_filename = ""
logfile = magi_directory + "/magi_server.log"

gene_names = []       # list of all unique gene target names
gene_colors = []      # list of colors for each unique target

# GPIO pins:
PWM_PIN = 19			# Heater PWM
FAN = 26				# Case fan power
STATUS_LED_PIN = 4		# System status LED
IMAGER_LED_PIN = 13		# Fluorescence LED