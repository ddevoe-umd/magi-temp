#! /bin/bash

# Create default package.json file:
npm init -y

# Install Electron as a development dependency in package.json:
npm install electron --save-dev

# Edit package.json fields:
npm version "1.0.3"  # version for "about" box

# Edit the name field in package.json:
file="package.json"
if [ ! -f "$file" ]; then
  echo "Error: File '$file' not found!"
  exit 1
fi
awk '
{
  if ($0 ~ /^[[:space:]]*"name":/) {
    $0="  \"name\": \"MAGI\","
  }
  print
}
' "$file" > temp.json && mv temp.json "$file"

# Edit the description field in package.json:
awk '
{
  if ($0 ~ /^[[:space:]]*"description":/) {
    $0="  \"description\": \"Multiplexed Array Gene Imager (MAGI)\","
  }
  print
}
' "$file" > temp.json && mv temp.json "$file"

# Create the index.js file for Electron:
cat << 'EOF' > index.js
const { app, BrowserWindow } = require('electron');
let mainWindow;
app.on('ready', () => {
    mainWindow = new BrowserWindow({ 
        width: 800, 
        height: 800,
        webPreferences: {
          nodeIntegration: true,    // Enable Node.js features
        },
        frame: false,               // Disable default title bar
    });
    mainWindow.loadFile('magi.html');

    // Quit when the main window is closed:
    mainWindow.on('closed', () => {
        mainWindow = null;      // Dereference the window object
        app.quit();             // and quit the application
    });

});
EOF

npm install electron-packager --save-dev

# MacOS:
npx electron-packager . MAGI --platform=darwin --arch=arm64 --overwrite

# Windows:
# npx electron-packager . MAGI --platform=win32 --arch=x64 --overwrite
