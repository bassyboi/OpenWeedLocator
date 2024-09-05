import sys
import socket
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget, QMessageBox, QHBoxLayout, QListWidget
from PyQt5.QtCore import pyqtSignal, QObject

# Define server host and port
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000

# Define CAN bus command codes and their corresponding actions
CAN_COMMANDS = {
    "pause": 0x301,
    "play": 0x302,
    "boom_flush": 0x303,
    "stop": 0x304,
    "save_config": 0x305
}

# Error codes display
ERROR_CODES = {
    0x401: "Camera Error",
    0x402: "Relay Error",
    0x403: "Processing Error",
    0x404: "Configuration Error"
}

class ClientHandlerThread(QObject):
    # Custom signals for communication
    update_status_signal = pyqtSignal(str)
    update_error_signal = pyqtSignal(str)
    update_client_list_signal = pyqtSignal()

    def __init__(self, client_socket, client_address, server):
        super().__init__()
        self.client_socket = client_socket
        self.client_address = client_address
        self.server = server
        self.running = True

    def run(self):
        """ Handle client communication. """
        self.update_status_signal.emit(f"Client connected from {self.client_address}")
        try:
            while self.running:
                message = self.client_socket.recv(1024).decode()
                if message:
                    self.update_status_signal.emit(f"Received from {self.client_address}: {message}")
        except Exception as e:
            self.update_error_signal.emit(f"Client connection error: {e}")
        finally:
            self.stop()

    def send_command(self, command):
        """ Send a command to the client. """
        try:
            self.client_socket.send(command.encode())
            self.update_status_signal.emit(f"Sent command to {self.client_address}: {command}")
        except Exception as e:
            self.update_error_signal.emit(f"Error sending data to {self.client_address}: {e}")

    def stop(self):
        """ Stop the client handler. """
        self.running = False
        self.client_socket.close()
        self.update_status_signal.emit(f"Client {self.client_address} disconnected.")
        self.server.remove_client(self)

class ServerThread(QObject):
    # Custom signals for communication
    update_status_signal = pyqtSignal(str)
    update_error_signal = pyqtSignal(str)
    update_client_list_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = []
        self.server_running = False

    def start_server(self):
        try:
            self.server_socket.bind((SERVER_HOST, SERVER_PORT))
            self.server_socket.listen(5)  # Listen for up to 5 client connections
            self.server_running = True
            threading.Thread(target=self.accept_clients, daemon=True).start()
            self.update_status_signal.emit("Server started. Waiting for client connections...")
        except Exception as e:
            self.update_error_signal.emit(f"Server error: {e}")

    def accept_clients(self):
        """ Accept new clients and start a new thread for each client. """
        while self.server_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_handler = ClientHandlerThread(client_socket, client_address, self)
                self.clients.append(client_handler)
                self.update_client_list_signal.emit()
                threading.Thread(target=client_handler.run, daemon=True).start()
            except Exception as e:
                self.update_error_signal.emit(f"Client connection error: {e}")

    def send_command_to_client(self, client_handler, command):
        """ Send a command to a specific client. """
        client_handler.send_command(command)

    def send_command_to_all(self, command):
        """ Send a command to all connected clients. """
        for client in self.clients:
            client.send_command(command)

    def remove_client(self, client_handler):
        """ Remove a client from the list when it disconnects. """
        if client_handler in self.clients:
            self.clients.remove(client_handler)
            self.update_client_list_signal.emit()

    def stop_server(self):
        """ Stop the server and disconnect all clients. """
        self.server_running = False
        for client in self.clients:
            client.stop()
        self.server_socket.close()
        self.update_status_signal.emit("Server stopped.")

class OwlControllerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Owl System Control Panel (Server)")
        self.setGeometry(100, 100, 600, 400)

        # Initialize server thread
        self.server_thread = ServerThread()
        self.server_thread.update_status_signal.connect(self.update_status)
        self.server_thread.update_error_signal.connect(self.update_error)
        self.server_thread.update_client_list_signal.connect(self.update_client_list)

        # Layout setup
        layout = QVBoxLayout()
        button_layout = QHBoxLayout()

        # Start Server Button
        self.start_server_button = QPushButton("Start Server")
        self.start_server_button.clicked.connect(self.start_server)
        layout.addWidget(self.start_server_button)

        # Stop Server Button
        self.stop_server_button = QPushButton("Stop Server")
        self.stop_server_button.clicked.connect(self.stop_server)
        layout.addWidget(self.stop_server_button)

        # CAN Command Buttons
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(lambda: self.send_command_to_all_clients("play"))
        button_layout.addWidget(self.play_button)

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(lambda: self.send_command_to_all_clients("pause"))
        button_layout.addWidget(self.pause_button)

        self.boom_flush_button = QPushButton("Boom Flush")
        self.boom_flush_button.clicked.connect(lambda: self.send_command_to_all_clients("boom_flush"))
        button_layout.addWidget(self.boom_flush_button)

        self.stop_command_button = QPushButton("Stop")
        self.stop_command_button.clicked.connect(lambda: self.send_command_to_all_clients("stop"))
        button_layout.addWidget(self.stop_command_button)

        self.save_config_button = QPushButton("Save Config")
        self.save_config_button.clicked.connect(lambda: self.send_command_to_all_clients("save_config"))
        button_layout.addWidget(self.save_config_button)

        layout.addLayout(button_layout)

        # Client List Widget
        self.client_list_widget = QListWidget()
        layout.addWidget(self.client_list_widget)

        # Status Label
        self.status_label = QLabel("Server Status: Not running")
        layout.addWidget(self.status_label)

        # Error Message Label
        self.error_label = QLabel("Error: None")
        layout.addWidget(self.error_label)

        # Set layout to a central widget
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def start_server(self):
        self.server_thread.start_server()

    def stop_server(self):
        self.server_thread.stop_server()

    def send_command_to_all_clients(self, command):
        self.server_thread.send_command_to_all(command)

    def update_client_list(self):
        self.client_list_widget.clear()
        for client in self.server_thread.clients:
            self.client_list_widget.addItem(f"{client.client_address}")

    def update_status(self, message):
        self.status_label.setText(message)

    def update_error(self, error_message):
        self.error_label.setText(f"Error: {error_message}")

def main():
    app = QApplication(sys.argv)
    mainWindow = OwlControllerApp()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
