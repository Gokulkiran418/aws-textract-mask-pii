import os
import cv2
import numpy as np
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from loguru import logger
from typing import List, Dict, Any

load_dotenv()


class TextractClient:
    def __init__(self) -> None:
        aws_region = os.getenv("AWS_REGION")
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not all([aws_region, access_key, secret_key]):
            raise EnvironmentError("Missing AWS credentials in environment variables.")

        self.client = boto3.client(
            "textract",
            region_name=aws_region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        logger.info("Textract client initialized.")

    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)
            success, processed_bytes = cv2.imencode(".png", enhanced)
            if not success:
                raise ValueError("Image encoding failed.")
            return processed_bytes.tobytes()
        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            raise RuntimeError(f"Image preprocessing error: {e}")

    async def analyze_document(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        processed_image = self._preprocess_image(image_bytes)
        try:
            logger.info("Calling Textract AnalyzeDocument API")
            response = self.client.analyze_document(
                Document={"Bytes": processed_image},
                FeatureTypes=["FORMS"],
            )
            blocks = response.get("Blocks", [])
            logger.debug(f"Textract returned {len(blocks)} blocks.")

            # 🔍 Extract and log visible text
            extracted_lines = [
                block["Text"]
                for block in blocks
                if block["BlockType"] == "LINE" and "Text" in block
            ]
            logger.info(f"Extracted {len(extracted_lines)} line(s) of text:")
            for line in extracted_lines:
                logger.info(f"📝 {line}")

            return blocks

        except ClientError as e:
            logger.exception("AWS Textract client error")
            raise RuntimeError(f"Textract API error: {e}")
        except Exception as e:
            logger.exception("Unexpected Textract error")
            raise RuntimeError(f"Unexpected error: {e}")
