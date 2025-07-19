import boto3
from botocore.exceptions import ClientError
from loguru import logger
import os
from dotenv import load_dotenv
import cv2
import numpy as np

load_dotenv()

class TextractClient:
    def __init__(self):
        self.client = boto3.client(
            "textract",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def preprocess_image(self, image_bytes: bytes) -> bytes:
        """Enhance image contrast and upscale for better OCR accuracy."""
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply histogram equalization
            equalized = cv2.equalizeHist(gray)

            # Upscale by 2x with Lanczos interpolation
            upscaled = cv2.resize(equalized, None, fx=2, fy=2, interpolation=cv2.INTER_LANCZOS4)

            # Encode back to bytes
            _, encoded_image = cv2.imencode(".png", upscaled)
            return encoded_image.tobytes()
        except Exception as e:
            logger.error(f"Preprocessing error: {e}")
            raise Exception(f"Failed to preprocess image: {e}")

    async def analyze_document(self, image_bytes: bytes):
        try:
            # Preprocess the image
            processed_image = self.preprocess_image(image_bytes)
            logger.info("Calling Textract AnalyzeDocument API with preprocessed image")
            response = self.client.analyze_document(
                Document={"Bytes": processed_image},
                FeatureTypes=["FORMS", "TABLES"],  # Capture structured data
                # Uncomment and adjust for Hindi/Tamil if needed
                # HumanReviewConfig={"Languages": [{"LanguageCode": "hi"}, {"LanguageCode": "ta"}]}
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
