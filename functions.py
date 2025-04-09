import os
import serial
import serial.tools.list_ports
import threading
import time
import math
from PyQt5.QtCore import (QObject, pyqtSignal, pyqtSlot, Qt, 
                         QPoint, QTimer, QRect)
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QGroupBox, QFormLayout, QPushButton, QFrame,
                           QProgressBar, QDial)
from PyQt5.QtGui import (QPainter, QColor, QPen, QPolygon, QFont,
                        QLinearGradient)

class VerticalGauge(QFrame):
    def __init__(self, title, min_val, max_val, unit):
        super().__init__()
        self.title = title
        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.value = min_val
        self.setFixedSize(100, 100)  # Reduced size
        self.setStyleSheet("background-color: #111; border-radius: 5px;")

    def set_value(self, value):
        self.value = value  # Don't clamp the value to min/max to allow scrolling
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate visible range based on current value
        visible_min = max(self.min_val, self.value - 15)  # Show 15 units below current
        visible_max = min(self.max_val, self.value + 15)  # Show 15 units above current
        visible_range = visible_max - visible_min
        
        # Draw scale
        painter.setPen(QPen(Qt.white, 2))
        painter.setFont(QFont('Arial', 8))
        
        for i in range(int(visible_min), int(visible_max) + 1, 2):
            y_pos = int(self.height() - ((i - visible_min) * (self.height()/visible_range)))
            if i % 5 == 0:  # Major markings
                painter.drawLine(25, y_pos, 50, y_pos)
                painter.drawText(55, y_pos + 5, f"{i}{self.unit}")
            else:  # Minor markings
                painter.drawLine(35, y_pos, 50, y_pos)
        
        # Draw needle at current value (centered)
        needle_pos = int(self.height()/2)  # Always center the current value
        painter.setPen(QPen(Qt.red, 3))
        painter.drawLine(10, needle_pos, 25, needle_pos)
        
        # Draw current value at bottom
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 10, QFont.Bold))
        painter.drawText(10, self.height()-5, f"{self.value:.1f}{self.unit}")

class TiltGauge(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedSize(350, 180)  # Wider and shorter
        self.angle = 0
        self.setStyleSheet("background-color: #111; border-radius: 5px;")

    def set_angle(self, angle):
        self.angle = max(-45, min(45, angle))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw arc background (-45 to +45 degrees)
        center_x = self.width() / 2
        center_y = self.height() - 20
        radius = 150
        
        # Draw the arc
        painter.setPen(QPen(Qt.white, 2))
        painter.drawArc(int(center_x - radius), int(center_y - radius), 
                       int(radius * 2), int(radius * 2), 
                       135 * 16, 270 * 16)  # 135° to 405° (270° span)
        
        # Draw angle markings
        painter.setFont(QFont('Arial', 8))
        for angle in range(-40, 41, 10):  # Every 10 degrees from -40 to +40
            rad = math.radians(angle)
            x1 = int(center_x + (radius-5) * math.sin(rad))
            y1 = int(center_y - (radius-5) * math.cos(rad))
            x2 = int(center_x + radius * math.sin(rad))
            y2 = int(center_y - radius * math.cos(rad))
            painter.drawLine(x1, y1, x2, y2)
            
            # Draw angle text
            if angle != 0:  # Skip 0 to reduce clutter
                text_x = int(center_x + (radius-20) * math.sin(rad)) - 10
                text_y = int(center_y - (radius-20) * math.cos(rad)) + 5
                painter.drawText(text_x, text_y, f"{angle}°")
        
        # Draw center line at 0°
        painter.drawLine(int(center_x - radius), int(center_y), 
                         int(center_x + radius), int(center_y))
        
        # Draw needle
        rad = math.radians(self.angle)
        x_end = int(center_x + (radius-10) * math.sin(rad))
        y_end = int(center_y - (radius-10) * math.cos(rad))
        painter.setPen(QPen(Qt.red, 3))
        painter.drawLine(int(center_x), int(center_y), x_end, y_end)
        
        # Draw current angle value
        painter.setPen(Qt.white)
        painter.setFont(QFont('Arial', 10, QFont.Bold))
        painter.drawText(10, 15, "TILT")
        painter.drawText(int(center_x - 20), 20, f"{self.angle:.1f}°")


class DataDisplay(QWidget):
    def __init__(self):
        super().__init__()
        self.value_names = ["Sensor 1", "Sensor 2", "Sensor 3", "Value", "Status"]
        self.value_units = ["", "", "", "", ""]
        self.flight_status = 0  # 0 = Not flying (landed), 1 = Flying (in air)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Flight Status Display
        self.status_display = QLabel("DRONE STATUS: LANDED")
        self.status_display.setAlignment(Qt.AlignCenter)
        self.status_display.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 8px;
                border: 2px solid #555;
                border-radius: 5px;
                background-color: #333;
                color: #ff5555;
            }
        """)
        layout.addWidget(self.status_display)
        
        # Control Buttons
        control_group = QGroupBox("Drone Control")
        control_layout = QHBoxLayout()
        
        self.takeoff_button = QPushButton("TAKE OFF")
        self.takeoff_button.setStyleSheet("""
            QPushButton {
                background-color: #2a2;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #3b3;
            }
            QPushButton:pressed {
                background-color: #181;
            }
        """)
        
        self.land_button = QPushButton("LAND")
        self.land_button.setStyleSheet("""
            QPushButton {
                background-color: #a22;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                min-height: 40px;
            }
            QPushButton:hover {
                background-color: #b33;
            }
            QPushButton:pressed {
                background-color: #811;
            }
        """)
        
        control_layout.addWidget(self.takeoff_button)
        control_layout.addWidget(self.land_button)
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Sensor Data Group
        data_group = QGroupBox("Sensor Data")
        data_layout = QFormLayout()
        
        self.value_labels = []
        for i in range(5):
            label = QLabel("0" + self.value_units[i])
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    font-weight: bold;
                    padding: 5px;
                    border: 1px solid #444;
                    border-radius: 3px;
                    background-color: #222;
                    color: #eee;
                    min-width: 80px;
                }
            """)
            data_layout.addRow(f"{self.value_names[i]}:", label)
            self.value_labels.append(label)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Instrumentation Group (only gauges now)
        instruments_group = QGroupBox("Drone Instruments")
        instruments_layout = QVBoxLayout()
        
        # Height and Speed in a row
        h_gauges = QHBoxLayout()
        self.height_gauge = VerticalGauge("HEIGHT", 0, 30, "m")  # Reduced range
        self.speed_gauge = VerticalGauge("SPEED", 0, 10, "m/s")  # Reduced range
        h_gauges.addWidget(self.height_gauge)
        h_gauges.addWidget(self.speed_gauge)
        instruments_layout.addLayout(h_gauges)
        
        # Tilt Gauge below
        self.tilt_gauge = TiltGauge()
        instruments_layout.addWidget(self.tilt_gauge)
        
        instruments_group.setLayout(instruments_layout)
        layout.addWidget(instruments_group)
        
        # Status Bar
        self.status_label = QLabel("System initialized")
        self.status_label.setStyleSheet("color: #aaa; font-style: italic;")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.setFixedWidth(400)

    def update_values(self, values):
        """Update both the numeric displays and gauges"""
        # Update sensor values
        for i in range(min(5, len(values))):
            if i == 3:  # Float value
                self.value_labels[i].setText(f"{values[i]:.1f}{self.value_units[i]}")
            else:
                self.value_labels[i].setText(f"{values[i]}{self.value_units[i]}")
        
        # Update gauges
        if len(values) > 0:
            self.height_gauge.set_value(values[0])
        if len(values) > 1:
            self.speed_gauge.set_value(values[1])
        if len(values) > 2:
            self.tilt_gauge.set_angle(values[2])

    def update_status(self, message):
        self.status_label.setText(message)
        
    def update_flight_status(self, status):
        """Update flight status display (0 = landed, 1 = flying)"""
        self.flight_status = status
        if status == 0:
            self.status_display.setText("DRONE STATUS: LANDED")
            self.status_display.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    padding: 8px;
                    border: 2px solid #555;
                    border-radius: 5px;
                    background-color: #333;
                    color: #ff5555;
                }
            """)
        else:
            self.status_display.setText("DRONE STATUS: FLYING")
            self.status_display.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    font-weight: bold;
                    padding: 8px;
                    border: 2px solid #555;
                    border-radius: 5px;
                    background-color: #333;
                    color: #55ff55;
                }
            """)

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
            <link rel="stylesheet" href="leaflet.css" />
            <script src="leaflet.js"></script>
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
                // Fixed center coordinates (your known location)
                var initialCenter = [28.402236, 76.988318];
                var initialZoom = 15;
                var resetTimer;
                
                var map = L.map('map').setView(initialCenter, initialZoom);
                
                // Use local tiles instead of online tiles
                // Assuming tiles are in a 'tiles' subdirectory
                L.tileLayer('tiles/{z}/{x}/{y}.png', {
                    maxZoom: 18,
                    minZoom: 12,
                    attribution: 'Map data © OpenStreetMap contributors',
                    errorTileUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII='
                }).addTo(map);
                
                // Add enemy marker
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
        """Threaded map loading"""
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
        self.current_values = [0, 0, 0, 0.0, '']  # int1, int2, int3, float_val, char_val

    def find_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if 'arduino' in port.description.lower() or 'CH340' in port.description.lower():
                return port.device
        return "COM7"

    def parse_data(self, data_string):
        """Parse $int,int,int,float,char format"""
        try:
            if not data_string.startswith('$'):
                return False
                
            parts = data_string[1:].strip().split(',')
            if len(parts) != 5:
                return False
                
            self.current_values = [
                int(parts[0]),
                int(parts[1]),
                int(parts[2]),
                float(parts[3]),
                parts[4][0] if parts[4] else ''
            ]
            return True
        except (ValueError, IndexError) as e:
            self.status_update.emit(f"Parse error: {str(e)}")
            return False

    def run(self):
        """Threaded serial reading"""
        self.port = self.find_arduino_port()
        self.status_update.emit(f"Connecting to {self.port}...")
        
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            self.status_update.emit("Serial connected. Waiting for data...")
            
            while self._running:
                if self.serial_conn.in_waiting:
                    data = self.serial_conn.readline().decode('utf-8').strip()
                    if self.parse_data(data):
                        self.data_processed.emit(self.current_values)
                time.sleep(0.01)
                
        except serial.SerialException as e:
            self.status_update.emit(f"Serial error: {str(e)}")
        finally:
            if self.serial_conn and self.serial_conn.is_open:
                self.serial_conn.close()
            self.status_update.emit("Serial processor stopped")
    
    def send_command(self, command):
        """Send a command to the connected serial device"""
        if self.serial_conn and self.serial_conn.is_open:
            try:
                self.serial_conn.write(command.encode('utf-8'))
                self.status_update.emit(f"Command sent: {command}")
                return True
            except Exception as e:
                self.status_update.emit(f"Failed to send command: {str(e)}")
                return False
        else:
            self.status_update.emit("Cannot send command: Serial not connected")
            return False

    def stop(self):
        self._running = False

class JSBridge(QObject):
    def __init__(self, window):
        super().__init__()
        self.window = window
    
    @pyqtSlot(str)
    def setDirection(self, direction):
        self.window.handle_direction(direction)