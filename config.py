
# Cross-module global variables:

well_config = []
well_cols = 4            # number of well columns
well_rows = 3            # number of well rows
roi_upper_left = (0,0)   # cordinates for upper left corner of upper left ROI
roi_width = 0            # box size
roi_height = 0 
roi_spacing_x = 0        # spacing between ROI centers
roi_spacing_y = 0        
ROIs = []                # list of upper left corners for all ROIs


card_filename = ""

target_dict = {          
  "MecA": ["#4C4CEB", "solid"],   
  "FemB": ["#5ED649", "solid"],
  "Nuc": ["#DD4444", "solid"],
  "POS": ["#222222", "dash"],
  "NEG": ["#555555", "dot"]
};
