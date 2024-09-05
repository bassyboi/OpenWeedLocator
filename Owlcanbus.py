#!/usr/bin/env python
import argparse
import cv2
import imutils
import zmq  # Import ZeroMQ
import time
import sys
import logging
import os
import numpy as np
import socket  # Added for client-server communication
from datetime import datetime
from multiprocessing import Value, Process
from threading import Thread
from configparser import ConfigParser
from pathlib import Path
from imutils.video import FPS
from utils.video import VideoStream
from utils.button_inputs import BasicController
from utils.image_sampler import ImageRecorder
from utils.blur_algorithms import fft_blur
from utils.greenonbrown import GreenOnBrown
from utils.greenongreen import GreenOnGreen
from utils.relay_control import RelayController, StatusIndicator
from utils.frame_reader import FrameReader
from utils.error_handler import ErrorHandler
from utils.custom_logger import setup_logger

# Define server host and port
SERVER_HOST = '127.0.0.1'  # Replace with server's IP address if needed
SERVER_PORT = 5000

# Define CAN bus command codes and their corresponding actions
CAN_COMMANDS = {
    "pause": "pause",
    "play": "play",
    "boom_flush": "boom_flush",
    "stop": "stop",
    "save_config": "save_config"
}

# Define custom error types and codes
ERROR_CODES = {
    0x401: "Camera Error",
    0x402: "Relay Error",
    0x403: "Processing Error",
    0x404: "Configuration Error"
}

class OwlClient:
    def __init__(self, show_display=False, focus=False, input_file_or_directory=None, config_file='config/DAY_SENSITIVITY_2.ini'):
        # Initialize logging
        setup_logger()

        # Initialize configuration
        self._config_path = Path(__file__).parent / config_file
        self.config = ConfigParser()
        self.config.read(self._config_path)

        # Initialize display and detection settings
        self.show_display = show_display
        self.focus = focus
        self.input_file_or_directory = input_file_or_directory
        self.disable_detection = False
        
        # Initialize controller settings
        self.enable_controller = self.config.getboolean('Controller', 'enable_controller')
        self.switch_purpose = self.config.get('Controller', 'switch_purpose')
        self.switch_pin = self.config.getint('Controller', 'switch_pin')

        # Setup controller and multiprocessing
        if self.enable_controller:
            self._setup_controller()

        # Setup camera and relay configurations
        self._setup_camera()
        self._setup_relays()

        # Initialize image sampling configuration
        self._setup_image_sampling()

        # Initialize client socket for server communication
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_server()

    def connect_to_server(self):
        """ Connect to the PyQt5 server. """
        try:
            self.client_socket.connect((SERVER_HOST, SERVER_PORT))
            print(f"Connected to server at {SERVER_HOST}:{SERVER_PORT}")
            # Start a thread to listen for commands from the server
            Thread(target=self.listen_for_commands, daemon=True).start()
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            sys.exit(1)

    def listen_for_commands(self):
        """ Listen for commands from the server and execute them. """
        while True:
            try:
                command = self.client_socket.recv(1024).decode()
                if command:
                    print(f"Received command: {command}")
                    self.execute_can_command(command)
            except Exception as e:
                print(f"Error receiving command: {e}")
                break

    def send_status_to_server(self, status_message):
        """ Send status messages back to the server. """
        try:
            self.client_socket.send(status_message.encode())
            print(f"[STATUS] Sent to server: {status_message}")
        except Exception as e:
            print(f"Error sending status to server: {e}")

    def _setup_controller(self):
        """ Setup button controller and related multiprocessing """
        self.detection_state = Value('b', False)
        self.sample_state = Value('b', False)
        self.stop_flag = Value('b', False)
        self.basic_controller = BasicController(detection_state=self.detection_state,
                                                sample_state=self.sample_state,
                                                stop_flag=self.stop_flag,
                                                switch_board_pin=f'BOARD{self.switch_pin}',
                                                switch_purpose=self.switch_purpose)
        self.basic_controller_process = Process(target=self.basic_controller.run)
        self.basic_controller_process.start()

    def _setup_camera(self):
        """ Setup camera or frame reader based on input source """
        self.resolution = (self.config.getint('Camera', 'resolution_width'),
                           self.config.getint('Camera', 'resolution_height'))
        self.exp_compensation = self.config.getint('Camera', 'exp_compensation')

        # Setup input source (camera or file/directory)
        try:
            if self.input_file_or_directory:
                self.cam = FrameReader(path=self.input_file_or_directory, resolution=self.resolution, loop_time=self.config.getint('Visualisation', 'image_loop_time'))
            else:
                self.cam = VideoStream(resolution=self.resolution, exp_compensation=self.exp_compensation).start()
            
            self.frame_width = self.cam.frame_width
            self.frame_height = self.cam.frame_height
        
        except Exception as e:
            self.report_error(0x401, f"Failed to initialize camera: {e}")
            self.stop()

    def _setup_relays(self):
        """ Setup relay configurations from the config file """
        try:
            self.relay_dict = {int(key): int(value) for key, value in self.config['Relays'].items()}
            self.relay_controller = RelayController(relay_dict=self.relay_dict)
            self.logger = self.relay_controller.logger
        except Exception as e:
            self.report_error(0x402, f"Relay setup error: {e}")
            self.stop()

    def _setup_image_sampling(self):
        """ Setup image sampling settings if enabled """
        self.sample_images = self.config.getboolean('DataCollection', 'sample_images')
        if self.sample_images:
            try:
                self.sample_method = self.config.get('DataCollection', 'sample_method')
                self.disable_detection = self.config.getboolean('DataCollection', 'disable_detection')
                self.sample_frequency = self.config.getint('DataCollection', 'sample_frequency')
                self.enable_device_save = self.config.getboolean('DataCollection', 'enable_device_save')
                self.save_directory = self.config.get('DataCollection', 'save_directory')
                self.camera_name = self.config.get('DataCollection', 'camera_name')

                self.indicators = StatusIndicator(save_directory=self.save_directory)
                self.save_subdirectory = self.indicators.setup_directories(enable_device_save=self.enable_device_save)
                self.indicators.start_storage_indicator()
                self.image_recorder = ImageRecorder(save_directory=self.save_subdirectory, mode=self.sample_method)
            except Exception as e:
                self.report_error(0x404, f"Configuration error during image sampling setup: {e}")
                self.stop()

    def report_error(self, error_code, error_message):
        """ Send a custom error message to the server """
        full_message = f"{error_code:x} {ERROR_CODES[error_code]}: {error_message}"
        self.send_status_to_server(full_message)
        print(f"[ERROR REPORT] Sent to server: {full_message}")

    def execute_can_command(self, command):
        """ Execute actions based on received CAN command. """
        if command == "pause":
            print("[ACTION] Pausing script...")
            # Implement pausing logic here
        elif command == "play":
            print("[ACTION] Playing script...")
            # Implement playing logic here
        elif command == "boom_flush":
            print("[ACTION] Boom Flush - Turning all relays ON!")
            self.relay_controller.relay.all_on()
        elif command == "stop":
            print("[ACTION] Stopping script...")
            self.stop()
        elif command == "save_config":
            print("[ACTION] Saving current configuration...")
            self.save_parameters()

    def hoot(self):
        """ Main processing loop for the Owl system. """
        algorithm = self.config.get('System', 'algorithm')
        log_fps = self.config.getboolean('DataCollection', 'log_fps')
        frame_count = 0

        if log_fps:
            fps = FPS().start()

        try:
            while True:
                if self.enable_controller:
                    self.disable_detection = not self.detection_state.value
                    self.sample_images = self.sample_state.value

                frame = self.cam.read()
                if frame is None:
                    if log_fps:
                        fps.stop()
                        print(f"[INFO] Stopped. Approximate FPS: {fps.fps():.2f}")
                    self.stop()
                    break

                # Perform detection and processing
                # ... [detection logic remains unchanged]

                frame_count += 1
                if log_fps:
                    fps.update()

                # Handle display
                # ... [existing display code remains unchanged]

                k = cv2.waitKey(1) & 0xFF
                if k == ord('s'):
                    self.save_parameters()
                elif k == 27:  # Escape key
                    self.stop()
                    break

        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.report_error(0x403, f"Processing error: {e}")
            self.stop()

    def stop(self):
        """ Stop the Owl system safely. """
        self.relay_controller.running = False
        self.relay_controller.relay.all_off()
        self.cam.stop()

        if self.enable_controller:
            self.basic_controller.stop()
            self.basic_controller_process.join()

        if self.sample_images:
            self.indicators.stop()
            self.image_recorder.stop()

        # Disconnect from server
        self.client_socket.close()
        print("[INFO] Disconnected from server.")

        if self.show_display:
            cv2.destroyAllWindows()

        sys.exit()

    def save_parameters(self):
        """ Save current configuration parameters to a new file. """
        try:
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            new_config_filename = f"{timestamp}_{self._config_path.name}"
            new_config_path = self._config_path.parent / new_config_filename

            # Update configuration parameters
            # ... [existing parameter saving code remains unchanged]

            print(f"[INFO] Configuration saved to {new_config_path}")
        except Exception as e:
            self.report_error(0x404, f"Failed to save configuration: {e}")

# Main script to run Owl system
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--show-display', action='store_true', default=False, help='show display windows')
    ap.add_argument('--focus', action='store_true', default=False, help='add FFT blur to output frame')
    ap.add_argument('--input', type=str, default=None, help='path to image directory, single image or video file')

    args = ap.parse_args()

    owl_client = OwlClient(config_file='config/DAY_SENSITIVITY_2.ini',
                           show_display=args.show_display,
                           focus=args.focus,
                           input_file_or_directory=args.input)

    # Start the main processing loop
    owl_client.hoot()
