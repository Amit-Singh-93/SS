import os
import random
from PyQt5.QtWidgets import (QVBoxLayout, QWidget, QHBoxLayout, 
                            QLabel, QGroupBox, QFormLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, Qt, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel

def create_html():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Leaflet Map</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
        <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
        <style>
            #controls {
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 1000;
                background: white;
                padding: 5px;
                border-radius: 4px;
                box-shadow: 0 0 5px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
                gap: 5px;
            }
            #controls button {
                margin: 0;
                padding: 5px 10px;
                font-size: 12px;
                width: 60px;
            }
            #zoom-controls {
                position: absolute;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: white;
                padding: 5px;
                border-radius: 4px;
                box-shadow: 0 0 5px rgba(0,0,0,0.2);
                display: flex;
                flex-direction: column;
                gap: 5px;
            }
            #directionPopup {
                position: absolute;
                top: 50px;
                left: 10px;
                background: white;
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-radius: 3px;
                z-index: 1000;
                display: none;
                font-size: 14px;
                box-shadow: 0 0 5px rgba(0,0,0,0.2);
            }
        </style>
    </head>
    <body>
        <div id="map" style="width: 100vw; height: 100vh;"></div>
        <div id="controls">
            <button id="northBtn">North</button>
            <button id="southBtn">South</button>
            <button id="eastBtn">East</button>
            <button id="westBtn">West</button>
        </div>
        <div id="zoom-controls">
            <button onclick="map.zoomIn()">Zoom In</button>
            <button onclick="map.zoomOut()">Zoom Out</button>
        </div>
        <div id="directionPopup"></div>
        <script>
            new QWebChannel(qt.webChannelTransport, function(channel) {
                window.pyQtBridge = channel.objects.pyQtBridge;
            });

            var initialCenter = [28.402236, 76.988318];
            var initialZoom = 15;
            var resetTimer;
            
            var map = L.map('map').setView(initialCenter, initialZoom);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
            
            L.marker([28.3968, 77.0233]).addTo(map).bindPopup("<h2>Enemy</h2>");
            
            var circles = [
                { radius: 4000, label: 'Fourth Circle' },
                { radius: 3000, label: 'Third Circle' },
                { radius: 2000, label: 'Second Circle' },
                { radius: 1000, label: 'First Circle' }
            ];
            
            function addCircles() {
                circles.forEach(function(circle) {
                    L.circle(initialCenter, {
                        radius: circle.radius,
                        color: 'blue',
                        fillColor: 'transparent',
                        fillOpacity: 0,
                        opacity: 1
                    }).addTo(map).bindPopup(circle.label)
                      .on('click', function(e) {
                          e.target.openPopup();
                      });
                });
            }
            addCircles();
            
            function resetMapView() {
                map.setView(initialCenter, initialZoom);
                addCircles();
            }
            
            function scheduleReset() {
                if (resetTimer) {
                    clearTimeout(resetTimer);
                }
                resetTimer = setTimeout(resetMapView, 2000);
            }
            
            document.getElementById('northBtn').addEventListener('click', function() {
                showDirection('North');
            });
            
            document.getElementById('southBtn').addEventListener('click', function() {
                showDirection('South');
            });
            
            document.getElementById('eastBtn').addEventListener('click', function() {
                showDirection('East');
            });
            
            document.getElementById('westBtn').addEventListener('click', function() {
                showDirection('West');
            });
            
            function showDirection(direction) {
                var popup = document.getElementById('directionPopup');
                popup.textContent = 'Direction set to ' + direction + '!';
                popup.style.display = 'block';
                setTimeout(function() {
                    popup.style.display = 'none';
                }, 1000);
                
                if (window.pyQtBridge) {
                    window.pyQtBridge.setDirection(direction);
                }
                scheduleReset();
            }
            
            map.on('moveend', scheduleReset);
            map.on('zoomend', scheduleReset);
            map.on('click', scheduleReset);
        </script>
    </body>
    </html>
    """
    file_path = os.path.abspath("map.html")
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(html_content)
    return file_path

class JSBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
    
    @pyqtSlot(str)
    def setDirection(self, direction):
        self.window.set_direction(direction)

class DroneStatusWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        layout = QFormLayout()
        
        self.speed_label = QLabel("0.0 m/s")
        self.altitude_label = QLabel("0.0 m")
        self.direction_label = QLabel("North")
        
        for label in [self.speed_label, self.altitude_label, self.direction_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 18px;
                    font-weight: bold;
                    padding: 10px;
                    border: 1px solid #ccc;
                    border-radius: 5px;
                    background-color: #f8f8f8;
                    min-width: 120px;
                }
            """)
        
        layout.addRow("Speed:", self.speed_label)
        layout.addRow("Altitude:", self.altitude_label)
        layout.addRow("Direction:", self.direction_label)
        
        group_box = QGroupBox("Drone Status")
        group_box.setLayout(layout)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(group_box)
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        self.setFixedWidth(200)
        
    def update_status(self, speed, altitude, direction=None):
        self.speed_label.setText(f"{speed:.1f} m/s")
        self.altitude_label.setText(f"{altitude:.1f} m")
        if direction is not None:
            self.direction_label.setText(direction)