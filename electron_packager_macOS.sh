#! /bin/bash

npm init -y
npm install electron --save-dev

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
npx electron-packager . MAGI --platform=darwin --arch=arm64 --overwrite