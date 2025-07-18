import cv2
import numpy as np
from loguru import logger
from typing import List, Dict

class ImageMasker:
    @staticmethod
    def mask_image(image_bytes: bytes, pii_fields: List[Dict], mask_type: str = "rectangle") -> bytes:
        try:
            # Convert bytes to OpenCV image
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")

            height, width = image.shape[:2]
            for field in pii_fields:
                bbox = field["bounding_box"]
                if not bbox:
                    continue
                x = int(bbox["Left"] * width)
                y = int(bbox["Top"] * height)
                w = int(bbox["Width"] * width)
                h = int(bbox["Height"] * height)

                if mask_type == "blur":
                    roi = image[y:y+h, x:x+w]
                    blurred = cv2.GaussianBlur(roi, (51, 51), 0)
                    image[y:y+h, x:x+w] = blurred
                else:  # Default to rectangle
                    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 0), -1)

            # Encode back to bytes
            _, encoded_image = cv2.imencode(".png", image)
            logger.info(f"Masked {len(pii_fields)} PII fields with {mask_type}")
            return encoded_image.tobytes()
        except Exception as e:
            logger.error(f"Masking error: {e}")
            raise Exception(f"Failed to mask image: {e}")