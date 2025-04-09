import sys
import os
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, 
                            QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QFileInfo
from PyQt5.QtWebChannel import QWebChannel
from functions import MapLoader, SerialProcessor, DataDisplay, JSBridge

class DroneControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Control System")
        self.setGeometry(100, 100, 1300, 800)
        
        # Initialize drone status (0 = landed, 1 = flying)
        self.drone_status = 0
        
        self.init_components()
        self.init_ui()
        self.check_required_files()
        self.init_threads()
        self.connect_signals()

    def init_components(self):
        """Initialize all application components"""
        self.map_loader = MapLoader()
        self.serial_processor = SerialProcessor()
        self.data_display = DataDisplay()
        self.web_view = QWebEngineView()
        self.js_bridge = JSBridge(self)

    def init_ui(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        
        # Left panel (data display and controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(self.data_display)
        left_layout.addStretch()
        layout.addWidget(left_panel)
        
        # Right panel (map)
        layout.addWidget(self.web_view, stretch=2)
        
        self.setCentralWidget(central_widget)

    def check_required_files(self):
        """Verify all required files for offline operation exist"""
        required_files = [
            'leaflet.js',
            'leaflet.css',
            os.path.join('tiles', '12'),  # Check for at least one zoom level
            'map.html'
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            msg = "Missing files for offline operation:\n" + "\n".join(missing_files)
            QMessageBox.warning(self, "Missing Files", 
                               f"{msg}\n\nPlease run map_utils.py to download tiles "
                               "and ensure all files are in place.")

    def init_threads(self):
        """Initialize and start all background threads"""
        self.threads = [
            threading.Thread(target=self.map_loader.run, daemon=True),
            threading.Thread(target=self.serial_processor.run, daemon=True)
        ]
        
        for thread in self.threads:
            thread.start()

    def connect_signals(self):
        """Connect all signals and slots"""
        # Map loader signals
        self.map_loader.map_ready.connect(self.load_map)
        self.map_loader.status_update.connect(
            self.data_display.update_status)
        
        # Serial processor signals
        self.serial_processor.data_processed.connect(
            self.data_display.update_values)
        self.serial_processor.status_update.connect(
            self.data_display.update_status)
        
        # Button connections
        self.data_display.takeoff_button.clicked.connect(self.takeoff)
        self.data_display.land_button.clicked.connect(self.land)
        
        # Set up web channel for JavaScript-Python communication
        self.web_channel = QWebChannel()
        self.web_channel.registerObject('pyQtBridge', self.js_bridge)
        self.web_view.page().setWebChannel(self.web_channel)

    def load_map(self, path):
        """
        Load the map HTML file with proper web channel setup
        Args:
            path (str): Path to the map HTML file
        """
        file_info = QFileInfo(path)
        if file_info.exists():
            url = QUrl.fromLocalFile(file_info.absoluteFilePath())
            self.web_view.setUrl(url)
        else:
            self.data_display.update_status("Map file not found")

    def handle_direction(self, direction):
        """
        Handle direction commands from the map
        Args:
            direction (str): Direction command (North/South/East/West)
        """
        if self.drone_status == 1:  # Only process movement if drone is flying
            self.data_display.update_status(f"Moving {direction}")
            # Send command to drone
            self.serial_processor.send_command(f"DIR:{direction}")
        else:
            self.data_display.update_status("Cannot move: Drone is not flying")

    def takeoff(self):
        """Handle takeoff button click"""
        if self.drone_status == 0:  # Only if currently landed
            # Confirm takeoff with a dialog
            reply = QMessageBox.question(
                self, 'Confirm Takeoff', 
                'Are you sure you want to take off?',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Update status immediately first
                self.drone_status = 1
                self.data_display.update_flight_status(1)
                self.data_display.update_status("Drone is now flying.")
                
                # Then send the command to the hardware
                self.serial_processor.send_command("CMD:TAKEOFF")
        else:
            self.data_display.update_status("Drone is already flying")

    def land(self):
        """Handle land button click"""
        if self.drone_status == 1:  # Only if currently flying
            # Update status immediately first
            self.drone_status = 0
            self.data_display.update_flight_status(0)
            self.data_display.update_status("Drone is landing.")
            
            # Then send the command to the hardware
            self.serial_processor.send_command("CMD:LAND")
        else:
            self.data_display.update_status("Drone is already landed")

    def closeEvent(self, event):
        """
        Handle window close event
        Args:
            event: Close event
        """
        # If drone is still flying, attempt to land it first
        if self.drone_status == 1:
            reply = QMessageBox.warning(
                self, 'Warning',
                'Drone is still flying. Land before exiting?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes)
            
            if reply == QMessageBox.Yes:
                # Update status first
                self.drone_status = 0
                self.data_display.update_flight_status(0)
                
                # Then send command
                self.serial_processor.send_command("CMD:LAND")
                self.data_display.update_status("Emergency landing initiated")
        
        # Clean up resources
        self.map_loader.stop()
        self.serial_processor.stop()
        for thread in self.threads:
            thread.join(timeout=1)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DroneControlApp()
    window.show()
    sys.exit(app.exec_())