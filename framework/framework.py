import docker
import time
import requests
import json
from qwen_vl_utils import process_vision_info
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
import ast
import base64
from PIL import Image
from io import BytesIO
import torch
from docker import errors

class Framework:
    def __init__(self, image_name="sampagon/cvaf:latest", ports=None):
        if ports is None:
            ports = {
                '5900/tcp': 5900,
                '8501/tcp': 8501,
                '6080/tcp': 6080,
                '8080/tcp': 8080,
                '5000/tcp': 5000
            }
        
        self.client = docker.from_env()
        self.image_name = image_name
        self.ports = ports
        self.container = None
        self.MIN_PIXELS = 256 * 28 * 28
        self.MAX_PIXELS = 1344 * 28 * 28
        self._SYSTEM = "Based on the screenshot of the page, I give a text description and you give its corresponding location. The coordinate represents a clickable location [x, y] for an element, which is a relative coordinate on the screenshot, scaled from 0 to 1."

        # Initialize AI Model
        self.model = Qwen2VLForConditionalGeneration.from_pretrained(
            "showlab/ShowUI-2B",
            torch_dtype=torch.bfloat16,
            device_map="cuda"
        )
        self.processor = AutoProcessor.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct", 
            min_pixels=self.MIN_PIXELS, 
            max_pixels=self.MAX_PIXELS
        )

    def start(self):
        try:
            print("🚀 Starting container...")
            self.container = self.client.containers.run(
                self.image_name,
                ports=self.ports,
                detach=True,
                tty=True,
                auto_remove=True
            )
        except errors.ImageNotFound:
            print("📥 Pulling desktop image from Docker Hub...")
            self.client.images.pull(self.image_name)
            self.container = self.client.containers.run(
                self.image_name,
                ports=self.ports,
                detach=True,
                tty=True,
                auto_remove=True
            )

        url = "http://127.0.0.1:6080"
        print("⏳ Waiting for the container to be ready...")
        while True:
            try:
                response = requests.get(url, timeout=2)
                if response.status_code == 200:
                    print(f"✅ Container started successfully with ID: {self.container.id}")
                    print("🌐 View desktop at http://127.0.0.1:8080")
                    break
            except requests.exceptions.RequestException:
                time.sleep(1)

    def stop(self):
        if self.container:
            self.container.stop()
            print(f"🛑 Container with ID: {self.container.id} has been stopped")
        else:
            print("⚠️ No container to stop.")

    def __command(self, action, text=None, coordinate=None):
        url = 'http://127.0.0.1:5000/perform_action'
        headers = {'Content-Type': 'application/json'}
        data = {'action': action, 'text': text, 'coordinate': coordinate}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            if response.ok:
                print(f"✅ Sent Command: {action} | Text: {text} | Coordinate: {coordinate}")
                return response.json()
            else:
                print(f"❌ API Error: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"🚨 Error sending command: {e}")
            return None

    def left_click(self, text=None, coordinate=None):
        return self.__command("left_click", text, coordinate)
    
    def right_click(self, text=None, coordinate=None):
        return self.__command("right_click", text, coordinate)
    
    def middle_click(self, text=None, coordinate=None):
        return self.__command("middle_click", text, coordinate)
    
    def double_click(self, text=None, coordinate=None):
        return self.__command("double_click", text, coordinate)
    
    def mouse_move(self, text=None, coordinate=None):
        return self.__command("mouse_move", text, coordinate)
    
    def left_click_drag(self, text=None, coordinate=None):
        return self.__command("left_click_drag", text, coordinate)
    
    def cursor_position(self, text=None, coordinate=None):
        return self.__command("cursor_position", text, coordinate)
    
    def screenshot(self):
        response = self.__command("screenshot")
        if response and "base64_image" in response:
            print("📸 Screenshot Captured")
            return response["base64_image"]
        print("⚠️ Screenshot API response missing 'base64_image'")
        return None

    def type(self, text=None, coordinate=None):
        return self.__command("type", text, coordinate)
    
    def key(self, text=None, coordinate=None):
        return self.__command("key", text, coordinate)

    def vision_system(self, query, retries=3):
        """Enhanced VLM vision processing with retries & better logs"""
        for attempt in range(retries):
            base64_image = self.screenshot()
            if not base64_image:
                print("❌ ERROR: Failed to capture screenshot")
                continue

            image_data = base64.b64decode(base64_image)
            image = Image.open(BytesIO(image_data))

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._SYSTEM},
                        {"type": "image", "image": image, "min_pixels": self.MIN_PIXELS, "max_pixels": self.MAX_PIXELS},
                        {"type": "text", "text": query}
                    ],
                }
            ]

            print(f"\n🔍 Attempt {attempt + 1} | VLM Request: {query}")
            text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            image_inputs, video_inputs = process_vision_info(messages)
            
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt"
            ).to("cuda")

            generated_ids = self.model.generate(**inputs, max_new_tokens=128)
            generated_ids_trimmed = [
                out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False
            )[0]

            print(f"📢 VLM Response: {output_text}")

            try:
                coords = ast.literal_eval(output_text)
                coords = [int(coords[0] * image.width), int(coords[1] * image.height)]
                print(f"✅ Found Coordinates: {coords}")
                return coords
            except (SyntaxError, ValueError):
                print(f"❌ ERROR: Failed to parse AI response - {output_text}")

        print(f"🚨 Vision System Failed after {retries} retries")
        return None
