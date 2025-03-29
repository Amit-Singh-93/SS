import os
import serial
import serial.tools.list_ports
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt, QPoint, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QGroupBox, QFormLayout, QPushButton, QFrame)
from PyQt5.QtGui import QPainter, QColor, QPen, QPolygon

class VerticalGauge(QFrame):
    def __init__(self, title, min_val, max_val, unit):
        super().__init__()
        self.title = title
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.value = min_val
        self.demo_mode = True
        self.direction = 1
        self.setFixedSize(120, 200)
        self.setStyleSheet("background-color: white; border: 1px solid black;")
        
        self.demo_timer = QTimer(self)
        self.demo_timer.timeout.connect(self.update_demo_value)
        self.demo_timer.start(100)

    def set_value(self, value):
        if self.demo_mode:
            self.demo_mode = False
            self.demo_timer.stop()
        self.value = min(max(value, self.min_val), self.max_val)
        self.update()

    def update_demo_value(self):
        if self.demo_mode:
            self.value += self.direction * (self.max_val/100)
            
            if self.value >= self.max_val:
                self.value = self.max_val
                self.direction = -1
            elif self.value <= self.min_val:
                self.value = self.min_val
                self.direction = 1
                
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw title
        painter.setPen(QPen(Qt.black, 1))
        painter.drawText(10, 15, self.title)
        
        # Draw scale markings
        range_val = self.max_val - self.min_val
        for i in range(self.min_val, self.max_val + 1, 5):
            y_pos = int(180 - ((i - self.min_val) * (160/range_val)))
            if i % 10 == 0:  # Main markings
                painter.drawLine(20, y_pos, 40, y_pos)
                painter.drawText(45, y_pos + 5, f"{i} {self.unit}")
            else:  # Sub markings
                painter.drawLine(30, y_pos, 40, y_pos)
        
        # Draw needle
        needle_pos = int(180 - ((self.value - self.min_val) * (160/range_val)))
        needle = QPolygon([
            QPoint(50, needle_pos),
            QPoint(70, needle_pos - 5),
            QPoint(70, needle_pos + 5)
        ])
        
        painter.setPen(QPen(Qt.red, 2))
        painter.setBrush(QColor(255, 0, 0))
        painter.drawPolygon(needle)

        if self.demo_mode:
            painter.setPen(QPen(Qt.blue, 1))
            # painter.drawText(10, 30, "DEMO")

class MapLoader(QObject):
    map_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._running = True
        self._html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Leaflet Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
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
                #map { width: 100vw; height: 100vh; }
            </style>
        </head>
        <body>
            <div id="map"></div>
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

    def run(self):
        self.status_update.emit("Loading map...")
        try:
            file_path = os.path.abspath("map.html")
            with open(file_path, "w") as f:
                f.write(self._html_content)
            self.map_ready.emit(file_path)
            self.status_update.emit("Map loaded successfully")
            
            while self._running:
                time.sleep(0.1)
        except Exception as e:
            self.status_update.emit(f"Map error: {str(e)}")

    def stop(self):
        self._running = False

class SerialProcessor(QObject):
    data_processed = pyqtSignal(list)
    status_update = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._running = True
        self.port = None
        self.baudrate = 57600
        self.serial_conn = None
        self.current_values = [0, 0, 0, 0.0, '', 0.0, 0.0]  # int1, int2, int3, float1, char, height, speed

    def find_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'arduino' in port.description.lower() or 'CH340' in port.description.lower():
                return port.device
        return None

    def parse_data(self, data_string):
        try:
            if not data_string.startswith('$'):
                return False
                
            parts = data_string[1:].strip().split(',')
            if len(parts) != 7:
                return False
                
            self.current_values = [
                int(parts[0]), int(parts[1]), int(parts[2]),  # int1, int2, int3
                float(parts[3]),  # float1
                parts[4][0] if parts[4] else '',  # char
                float(parts[5]),  # height
                float(parts[6])   # speed
            ]
            return True
        except (ValueError, IndexError) as e:
            self.status_update.emit(f"Parse error: {str(e)}")
            return False

    def run(self):
        self.port = self.find_arduino_port()
        
        if not self.port:
            self.status_update.emit("No Arduino port found")
            return
            
        self.status_update.emit(f"Connecting to {self.port}...")
        
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.status_update.emit("Serial connected. Waiting for data...")
            
            while self._running and self.serial_conn.is_open:
                if self.serial_conn.in_waiting:
                    data = self.serial_conn.readline().decode('utf-8').strip()
                    if self.parse_data(data):
                        self.data_processed.emit(self.current_values)
                time.sleep(0.01)
                
        except serial.SerialException as e:
            if self._running:
                self.status_update.emit(f"Serial error: {str(e)}")
        finally:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()

    def stop(self):
        self._running = False

class DataDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.value_names = ["Sensor 1", "Sensor 2", "Sensor 3", "Value", "Status", "Height", "Speed"]
        self.value_units = ["", "", "", "", "", "m", "m/s"]
        self.height_gauge = VerticalGauge("Height", 0, 100, "m")
        self.speed_gauge = VerticalGauge("Speed", 0, 30, "m/s")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Data Display Group
        data_group = QGroupBox("Sensor Data")
        data_layout = QFormLayout()
        
        self.value_labels = []
        for i in range(7):
            label = QLabel("0" + self.value_units[i])
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    border: 1px solid #ddd;
                    border-radius: 3px;
                    background-color: #f9f9f9;
                    min-width: 80px;
                }
            """)
            data_layout.addRow(f"{self.value_names[i]}:", label)
            self.value_labels.append(label)
        
        data_group.setLayout(data_layout)
        
        # Gauges Group
        gauges_group = QGroupBox("Instrumentation")
        gauges_layout = QHBoxLayout()
        gauges_layout.addWidget(self.height_gauge)
        gauges_layout.addWidget(self.speed_gauge)
        gauges_group.setLayout(gauges_layout)
        
        # Status Bar
        self.status_label = QLabel("System initialized")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        
        layout.addWidget(data_group)
        layout.addWidget(gauges_group)
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        self.setLayout(layout)
        self.setFixedWidth(350)

    def update_values(self, values):
        for i in range(min(len(values), len(self.value_labels))):
            if i in [3, 5, 6]:  # Float values
                self.value_labels[i].setText(f"{values[i]:.2f}{self.value_units[i]}")
            else:
                self.value_labels[i].setText(f"{values[i]}{self.value_units[i]}")
        
        if len(values) > 5:
            self.height_gauge.set_value(float(values[5]))
        if len(values) > 6:
            self.speed_gauge.set_value(float(values[6]))

    def update_status(self, message):
        self.status_label.setText(message)

class JSBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
    
    @pyqtSlot(str)
    def setDirection(self, direction):
        self.window.handle_direction(direction)










