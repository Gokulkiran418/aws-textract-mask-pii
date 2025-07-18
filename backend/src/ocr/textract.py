import boto3
from botocore.exceptions import ClientError
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()

class TextractClient:
    def __init__(self):
        self.client = boto3.client(
            "textract",
            region_name=os.getenv("AWS_REGION"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    async def analyze_document(self, image_bytes: bytes):
        try:
            logger.info("Calling Textract AnalyzeDocument API")
            response = self.client.analyze_document(
                Document={"Bytes": image_bytes},
                FeatureTypes=["FORMS"],
            )
            logger.debug(f"Textract response: {response}")
            return response["Blocks"]
        except ClientError as e:
            logger.error(f"Textract error: {e}")
            raise Exception(f"Textract API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Textract: {e}")
            raise Exception(f"Unexpected error: {e}")