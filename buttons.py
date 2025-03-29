import sys
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, 
                            QVBoxLayout, QHBoxLayout)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
from PyQt5.QtWebChannel import QWebChannel
from functions import MapLoader, SerialProcessor, DataDisplay, JSBridge

class DroneControlApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Drone Control System")
        self.setGeometry(100, 100, 1300, 800)
        
        self.init_components()
        self.init_ui()
        self.init_threads()
        self.connect_signals()

    def init_components(self):
        self.map_loader = MapLoader()
        self.serial_processor = SerialProcessor()
        self.data_display = DataDisplay()
        self.web_view = QWebEngineView()
        self.js_bridge = JSBridge(self)

    def init_ui(self):
        central_widget = QWidget()
        layout = QHBoxLayout(central_widget)
        
        # Left panel
        layout.addWidget(self.data_display)
        
        # Right panel
        layout.addWidget(self.web_view, stretch=2)
        
        self.setCentralWidget(central_widget)

    def init_threads(self):
        self.threads = [
            threading.Thread(target=self.map_loader.run),
            threading.Thread(target=self.serial_processor.run)
        ]
        
        for thread in self.threads:
            thread.start()

    def connect_signals(self):
        self.map_loader.map_ready.connect(
            lambda path: self.web_view.setUrl(QUrl.fromLocalFile(path)))
        self.map_loader.status_update.connect(
            self.data_display.update_status)
        
        self.serial_processor.data_processed.connect(
            self.data_display.update_values)
        self.serial_processor.status_update.connect(
            self.data_display.update_status)
        
        self.web_channel = QWebChannel()
        self.web_channel.registerObject('pyQtBridge', self.js_bridge)
        self.web_view.page().setWebChannel(self.web_channel)

    def handle_direction(self, direction):
        self.data_display.update_status(f"Moving {direction}")

    def closeEvent(self, event):
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




