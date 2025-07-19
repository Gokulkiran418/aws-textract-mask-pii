import boto3
from botocore.exceptions import ClientError
from loguru import logger
import os
from dotenv import load_dotenv
import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from typing import List, Dict

load_dotenv()

class TextractClient:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = r"D:/Tesseract/tesseract.exe"
        self.client = boto3.client(
            "textract",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def preprocess_image(self, image_bytes: bytes) -> bytes:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        equalized = cv2.equalizeHist(gray)
        upscaled = cv2.resize(equalized, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)
        _, encoded_image = cv2.imencode(".png", upscaled)
        return encoded_image.tobytes()

    def extract_text_with_tesseract(self, image_bytes: bytes, lang: str) -> List[Dict]:
        try:
            # Decode image bytes to OpenCV format
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")

            # Use Tesseract to extract text with bounding box data
            data = pytesseract.image_to_data(image, lang=lang, output_type=Output.DICT)

            # Group words into lines and compute bounding boxes
            lines = {}
            for i in range(len(data['level'])):
                if data['level'][i] == 4:  # Line-level data
                    line_key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
                    if line_key not in lines:
                        lines[line_key] = {
                            'text': [],
                            'left': data['left'][i],
                            'top': data['top'][i],
                            'right': data['left'][i] + data['width'][i],
                            'bottom': data['top'][i] + data['height'][i]
                        }
                    lines[line_key]['text'].append(data['text'][i])
                    # Update bounding box coordinates
                    lines[line_key]['left'] = min(lines[line_key]['left'], data['left'][i])
                    lines[line_key]['top'] = min(lines[line_key]['top'], data['top'][i])
                    lines[line_key]['right'] = max(lines[line_key]['right'], data['left'][i] + data['width'][i])
                    lines[line_key]['bottom'] = max(lines[line_key]['bottom'], data['top'][i] + data['height'][i])

            # Convert to a list of dictionaries with normalized bounding boxes
            line_list = []
            img_height, img_width = image.shape[:2]
            for line_key, line_data in lines.items():
                text = ' '.join(line_data['text']).strip()
                if text:
                    bounding_box = {
                        'Width': (line_data['right'] - line_data['left']) / img_width,
                        'Height': (line_data['bottom'] - line_data['top']) / img_height,
                        'Left': line_data['left'] / img_width,
                        'Top': line_data['top'] / img_height
                    }
                    word_confs = [float(data['conf'][j]) for j in range(len(data['level']))
                                 if data['block_num'][j] == line_key[0] and
                                 data['par_num'][j] == line_key[1] and
                                 data['line_num'][j] == line_key[2] and
                                 data['level'][j] == 5]
                    confidence = sum(word_confs) / len(word_confs) if word_confs else 0.0
                    line_list.append({
                        'text': text,
                        'bounding_box': bounding_box,
                        'confidence': confidence
                    })
            logger.debug(f"Tesseract extracted {len(line_list)} lines with bounding boxes")
            return line_list
        except Exception as e:
            logger.error(f"Tesseract error: {e}")
            raise Exception(f"Failed to extract text with Tesseract: {e}")

    async def analyze_document(self, image_bytes: bytes):
        try:
            processed_image = self.preprocess_image(image_bytes)
            logger.info("Calling Textract AnalyzeDocument API with preprocessed image")
            response = self.client.analyze_document(
                Document={"Bytes": processed_image},
                FeatureTypes=["FORMS", "TABLES"],
            )
            logger.debug(f"Textract returned {len(response['Blocks'])} blocks.")
            logger.info(f"Extracted {len([b for b in response['Blocks'] if b['BlockType'] == 'LINE'])} line(s) of text:")
            for block in response["Blocks"]:
                if block["BlockType"] == "LINE":
                    logger.info(f"📝 {block.get('Text', 'No text')}")
            return response["Blocks"]
        except ClientError as e:
            logger.error(f"Textract error: {e}")
            raise Exception(f"Textract API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Textract: {e}")
            raise Exception(f"Unexpected error: {e}")