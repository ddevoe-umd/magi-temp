Multiplexed Array Gene Imager (MAGI)
-

Hardware:
-
* Raspberry Pi Zero 2 W (Python3, Raspberry Pi OS)
* Pi Camera (InnoMaker CAM OV5647, 5MP)

Installation 
-
* Install Python modules, set up ram disk, Synchronize Pi system time, and modify rc.local to start server at boot:
   `sudo ./setup.sh`

Operation:
-
Open `magi.html` on the client laptop

Pi:
-
* `magi_server.py`
	- set up to launch on boot via `/etc/rc.local`
	- handle Javascript client <--> Python server communication
	- manage PID control of heater
	- access `imager.py` to send data to client
* `imager.py`
	- get & process data from the camera
* `filter_curves.py`
	- filter noise and evaluate time-to-positive values

Client:
-
* `magi.html`
	- client user interface
* `css/style.css`
	- style sheet for plot.html
* `js/canvasjs.min.js`
	- Javascript code for plotting (js folder must be in same directory as `plot.html`)
* `fonts/OpenSans.ttf`
	- Truetype font for image annotations
