from hailo_platform import VDevice, HEF, InputVStreams, OutputVStreams
from pathlib import Path
import cv2
import numpy as np

class GreenOnGreen:
    def __init__(self, model_path='models', label_file='models/labels.txt'):
        if model_path is None:
            print('[WARNING] No model directory or path provided with --model-path flag. '
                  'Attempting to load from default...')
            model_path = 'models'
        self.model_path = Path(model_path)

        if self.model_path.is_dir():
            model_files = list(self.model_path.glob('*.hef'))
            if not model_files:
                raise FileNotFoundError('No .hef model files found. Please provide a directory or .hef file.')
            else:
                self.model_path = model_files[0]
                print(f'[INFO] Using {self.model_path.stem} model...')
        elif self.model_path.suffix == '.hef':
            print(f'[INFO] Using {self.model_path.stem} model...')
        else:
            print(f'[WARNING] Specified model path {model_path} is unsupported, attempting to use default...')
            model_files = Path('models').glob('*.hef')
            try:
                self.model_path = next(model_files)
                print(f'[INFO] Using {self.model_path.stem} model...')
            except StopIteration:
                print('[ERROR] No model files found.')

        # Read labels
        self.labels = self.read_label_file(label_file)

        # Load HEF model
        self.hef = HEF(self.model_path.as_posix())

        # Create a VDevice
        self.vdevice = VDevice()

        # Configure the HEF
        self.network_groups = self.vdevice.configure(self.hef)
        self.network_group = self.network_groups[0]

        # Get input and output VStreams infos
        self.input_vstream_infos = self.network_group.get_input_vstream_infos()
        self.output_vstream_infos = self.network_group.get_output_vstream_infos()

        # Get input shape
        self.input_shape = self.input_vstream_infos[0].shape  # Assuming single input

        # Get output names
        self.output_names = [info.name for info in self.output_vstream_infos]
        self.output_shapes = [info.shape for info in self.output_vstream_infos]

        print("Output VStreams:")
        for info in self.output_vstream_infos:
            print(f"Name: {info.name}, Shape: {info.shape}")

    def read_label_file(self, label_file):
        labels = {}
        with open(label_file, 'r') as f:
            for line in f:
                pair = line.strip().split(' ', 1)
                if len(pair) == 2:
                    labels[int(pair[0])] = pair[1]
        return labels

    def inference(self, image, confidence=0.5, filter_id=0):
        # Preprocess the image
        height, width, _ = image.shape
        input_height, input_width, input_channels = self.input_shape

        # Resize and convert image to the required shape
        resized_image = cv2.resize(image, (input_width, input_height))
        if input_channels == 3:
            # Assuming the model expects RGB images
            input_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB)
        else:
            # Assuming grayscale
            input_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)

        # Normalize or preprocess the image if necessary
        # Assuming the model expects uint8 images in [0, 255]
        input_image = input_image.astype(np.uint8)

        # Run inference
        # Wrap the input in a list if necessary
        input_data = [input_image]

        # Write input data to the input VStreams
        self.input_vstreams.write(input_data)

        # Read output data from the output VStreams
        output_data = self.output_vstreams.read()

        # Map outputs
        outputs = dict(zip(self.output_names, output_data))

        # Assuming the output tensors are 'detection_boxes', 'detection_classes', 'detection_scores'
        boxes = outputs.get('detection_boxes')
        classes = outputs.get('detection_classes')
        scores = outputs.get('detection_scores')

        if boxes is None or classes is None or scores is None:
            print("Output tensors not found.")
            return None, [], [], image

        # Now process the detections
        self.weed_centers = []
        self.boxes = []

        num_detections = boxes.shape[0]

        for i in range(num_detections):
            if scores[i] >= confidence and classes[i] == filter_id:
                # Scale the bounding box back to the original image size
                ymin, xmin, ymax, xmax = boxes[i]
                startX = int(xmin * width)
                startY = int(ymin * height)
                endX = int(xmax * width)
                endY = int(ymax * height)
                boxW = endX - startX
                boxH = endY - startY

                # Save the bounding box
                self.boxes.append([startX, startY, boxW, boxH])
                # Compute box center
                centerX = int(startX + (boxW / 2))
                centerY = int(startY + (boxH / 2))
                self.weed_centers.append([centerX, centerY])

                percent = int(100 * scores[i])
                label = f'{percent}% {self.labels.get(classes[i], classes[i])}'
                cv2.rectangle(image, (startX, startY), (endX, endY), (0, 0, 255), 2)
                cv2.putText(image, label, (startX, startY + 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
        return None, self.boxes, self.weed_centers, image

