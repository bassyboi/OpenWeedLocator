Adding Green-on-Green to the OWL (beta) with Hailo AI and YOLO Models

Welcome to the first iteration of Green-on-Green (in-crop weed detection) with the OpenWeedLocator (OWL) using Hailo AI hardware and YOLO models. This is an early beta version and may require additional troubleshooting. It has been tested and works on both a Raspberry Pi 5 and a Windows desktop computer.
Stage 1 | Hardware/Software - Hailo AI Installation

In addition to the standard software required to run the OWL, you'll need to install the Hailo SDK on your Raspberry Pi 5. Follow the instructions below to set up the Hailo AI environment.
Step 1: Download Hailo SDK

First, you need to download the Hailo SDK suitable for your Raspberry Pi 5. Visit the Hailo Developer Zone to get the latest SDK package.

Alternatively, you can download it directly to your Raspberry Pi using the command line (make sure to update the URL to the latest version):

bash

wget https://hailo.ai/wp-content/uploads/2021/10/hailo-sdk-4.15.0-1.deb

(Note: Replace the URL with the latest SDK version available on the Hailo website.)
Step 2: Install the SDK

Install the SDK package using dpkg:

bash

sudo dpkg -i hailo-sdk-4.15.0-1.deb

If you encounter dependency issues, run:

bash

sudo apt-get install -f

Then, re-run the installation command:

bash

sudo dpkg -i hailo-sdk-4.15.0-1.deb

Step 3: Set Up Environment Variables

After installing the SDK, you need to set up the environment variables. Run:

bash

source /usr/local/hailo_sdk/setup_env.sh

To make this change permanent, add the command to your ~/.bashrc file:

bash

echo "source /usr/local/hailo_sdk/setup_env.sh" >> ~/.bashrc

Step 4: Install Additional Dependencies

Install any additional dependencies required by the Hailo SDK and your application:

bash

sudo apt-get update
sudo apt-get install -y python3-pip python3-opencv libopencv-dev
pip3 install numpy

Step 5: Verify the Installation

To ensure the SDK is correctly installed, run one of the sample applications provided by Hailo:

bash

cd /usr/local/hailo_sdk/samples/common/python/classification
python3 classification_example.py

If the sample runs successfully and outputs classification results, your Hailo SDK installation is complete.
Stage 2 | Model Training/Deployment - Inference with Hailo AI and YOLO Models

Running weed recognition models on the Hailo AI hardware requires compiling your trained model into a Hailo Executable Format (.hef) file using the Hailo Dataflow Compiler. In this section, we'll focus on using YOLO models, which are well-suited for object detection tasks like weed detection.
Option 1 | Using a Pre-Trained YOLO Model from Hailo Model Zoo

Hailo provides pre-compiled YOLO models in their Model Zoo, which you can use directly.
Step 1: Download a Sample HEF YOLO Model

Navigate to the models directory in your OWL repository:

bash

cd ~/owl/models

Download a sample YOLOv5 HEF model, such as the YOLOv5s model trained on the COCO dataset:

bash

wget https://hailo.ai/wp-content/uploads/2021/05/yolov5s_coco.hef

(Note: Ensure the download link is up-to-date by checking the Hailo Model Zoo.)
Step 2: Obtain the Labels File

Download the labels file corresponding to the COCO dataset:

bash

wget https://raw.githubusercontent.com/ultralytics/yolov5/master/data/coco.names -O labels.txt

Step 3: Test the Model with OWL

Change back to the OWL directory and run owl.py with the Green-on-Green algorithm:

bash

cd ~/owl
python3 owl.py --show-display --algorithm gog

If you're testing indoors and the image appears dark, adjust the camera settings:

bash

python3 owl.py --show-display --algorithm gog --exp-compensation 4 --exp-mode auto

A video feed should appear, showing detections with red bounding boxes. By default, the code filters for 'potted plants' (class ID 63). To detect other categories, change the filter_id parameter in the inference method or pass it as a command-line argument.
Step 4: Verify the Detection

If the application runs correctly and you see detections on the video feed, your setup is working. You can proceed to train and deploy your own weed recognition YOLO models.
Option 2 | Train and Deploy Custom YOLO Models Using Hailo SDK

To detect specific weeds, you'll need to train a custom YOLO model and compile it for the Hailo AI hardware.
Step 1: Prepare Your Dataset

Gather images of weeds and crops to create a dataset. Label the images using annotation tools like LabelImg or Roboflow. Ensure that your annotations are in the YOLO format.
Step 2: Train Your YOLO Model

You can use YOLOv5 or YOLOv8 from Ultralytics to train your model.
Using YOLOv5

    Clone the YOLOv5 Repository:

    bash

git clone https://github.com/ultralytics/yolov5.git
cd yolov5
pip install -r requirements.txt

Prepare Your Dataset:

Organize your dataset according to the YOLOv5 directory structure and create a dataset YAML file.

Train the Model:

bash

    python train.py --img 640 --batch 16 --epochs 100 --data your_dataset.yaml --weights yolov5s.pt --cache

Using YOLOv8

    Install Ultralytics YOLOv8:

    bash

pip install ultralytics

Train the Model:

bash

    yolo train model=yolov8s.pt data=your_dataset.yaml epochs=100 imgsz=640

Step 3: Export the Model to ONNX Format

After training, export the model to ONNX format, which is compatible with the Hailo Dataflow Compiler.
For YOLOv5:

bash

python export.py --weights runs/train/exp/weights/best.pt --include onnx

For YOLOv8:

bash

yolo export model=runs/detect/train/weights/best.pt format=onnx

Step 4: Compile the Model with Hailo Dataflow Compiler

Use the Hailo SDK to compile your ONNX model into a HEF file.

bash

hailomvc compile -m best.onnx -o models/your_model.hef

(Note: The hailomvc command is part of the Hailo SDK and may have specific parameters you need to set. Refer to the Hailo SDK documentation for details.)

Important: YOLO models may require specific pre- and post-processing steps, and the Hailo compiler may have templates or examples for compiling YOLO models. Check the Hailo documentation or examples for compiling YOLO models to HEF.
Step 5: Update the Labels File

Create or update the labels.txt file with your custom classes. Each line should contain a class name corresponding to the class indices used during training.

Example labels.txt:

0 Thistle
1 Dandelion
2 Crop

Step 6: Adjust the Inference Code

Ensure that your GreenOnGreen class and inference code handle the YOLO model's output format. YOLO models output bounding boxes, class IDs, and confidence scores in a specific format.

Update the inference method in your code to parse the outputs accordingly.

Here's an example of how you might adjust the inference method:

python

def inference(self, image, confidence=0.5, filter_id=0):
    # Preprocess the image
    input_image = cv2.resize(image, (self.input_width, self.input_height))
    input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
    input_image = input_image.astype(np.float32) / 255.0
    input_image = np.transpose(input_image, (2, 0, 1))  # Convert to CHW format if required
    input_image = np.expand_dims(input_image, axis=0)

    # Run inference
    self.input_vstreams.write([input_image])

    # Read output data from the output VStreams
    output_data = self.output_vstreams.read()

    # Process the outputs according to YOLO format
    detections = self.post_process_outputs(output_data)

    # Now process the detections
    self.weed_centers = []
    self.boxes = []

    for detection in detections:
        class_id = int(detection['class_id'])
        score = detection['score']
        bbox = detection['bbox']  # [xmin, ymin, xmax, ymax] normalized coordinates

        if score >= confidence and class_id == filter_id:
            # Scale the bounding box back to the original image size
            xmin, ymin, xmax, ymax = bbox
            startX = int(xmin * image.shape[1])
            startY = int(ymin * image.shape[0])
            endX = int(xmax * image.shape[1])
            endY = int(ymax * image.shape[0])

            boxW = endX - startX
            boxH = endY - startY

            # Save the bounding box
            self.boxes.append([startX, startY, boxW, boxH])
            # Compute box center
            centerX = int(startX + (boxW / 2))
            centerY = int(startY + (boxH / 2))
            self.weed_centers.append([centerX, centerY])

            percent = int(100 * score)
            label = f'{percent}% {self.labels.get(class_id, class_id)}'
            cv2.rectangle(image, (startX, startY), (endX, endY), (0, 0, 255), 2)
            cv2.putText(image, label, (startX, startY + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
    return None, self.boxes, self.weed_centers, image

Ensure that you implement the post_process_outputs method to handle YOLO-specific post-processing, such as decoding the outputs and applying Non-Maximum Suppression (NMS). The exact implementation will depend on the output format of your YOLO model compiled for Hailo.

Note: The Hailo SDK may provide utilities or examples for handling YOLO model outputs. Refer to the Hailo documentation or example projects for guidance.
Step 7: Run the OWL Application with Your Custom YOLO Model

Execute the owl.py script with your custom HEF model:

bash

python3 owl.py --show-display --algorithm models/your_model.hef

Ensure the algorithm parameter points to your .hef file. Adjust the filter_id to match the class ID of the weed you want to detect.
References

These resources were helpful in developing this aspect of the project:

    Hailo Developer Zone
    Hailo SDK Documentation
    Hailo Model Zoo
    Hailo GitHub Examples
    Ultralytics YOLOv5 Repository
    Ultralytics YOLOv8 Repository
    YOLOv5 Export Tutorial
    Hailo YOLOv5 Example

    https://www.youtube.com/redirect?event=video_description&redir_token=QUFFLUhqa0g4Y0xtSUd5UXhWOGtISjRjR2htcVI1bHR3Z3xBQ3Jtc0tuSWpXeExQMHdlLUVrNzVGZlQwMzM3Y3ZWVndJazAtb1VzUWRpTk45NzcwX0FhUXJyS2hVZFJMdkRBUmU2WnROcldnQmxBQnl4WXlaRS1RbFhlSWNHa2Y5VnAwVlM0YTRDWmRkRkl2UTlHTjBVaGlBYw&q=https%3A%2F%2Fmy.cytron.io%2Ftutorial%2Fraspberry-pi-ai-kit-custom-object-detection-with-h%3Fr%3D1&v=7pgSFgqo8gY

Note: This is an early version of the approach and may be subject to change. If you encounter issues or have suggestions for improvement, please contribute to the project or reach out to the maintainers.
