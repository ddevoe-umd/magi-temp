
# Cross-module Python global variables:

well_config = []
roi_upper_left = (0,0)   # cordinates for upper left corner of upper left ROI
roi_width = 0            # box size
roi_height = 0 
roi_spacing_x = 0        # spacing between ROI centers
roi_spacing_y = 0        
ROIs = []                # list of upper left corners for all ROIs

card_filename = ""

# target_dict is currently copied from magi.js...need to make this come from file...
target_dict = {          
  "mecA": ["#4C4CEB", "solid"],   
  "femB": ["#5ED649", "solid"],
  "ermB": ["#FFC0CB", "solid"],
  "ermF": ["#33CCFF", "solid"],
  "ermT": ["#FF8C00", "solid"],
  "ermX": ["#FFFF00", "solid"],
  "tetA/C": ["#FF0000 ", "solid"],
  "sul1": ["#000080", "solid"],
  "sul2": ["#C0C0C0", "solid"],
  "nuc": ["#DD4444", "solid"],
  "POS": ["#222222", "dash"],
  "NEG": ["#555555", "dot"]
};
