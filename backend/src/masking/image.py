import cv2
import numpy as np
from loguru import logger
from typing import List, Dict

class ImageMasker:
    @staticmethod
    def mask_image(image_bytes: bytes, pii_fields: List[Dict], mask_type: str = "rectangle") -> bytes:
        try:
            # Decode image bytes
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")

            height, width = image.shape[:2]
            masked_fields = 0

            for field in pii_fields:
                bbox = field.get("bounding_box", {})
                if not bbox or "Left" not in bbox or "Top" not in bbox or "Width" not in bbox or "Height" not in bbox:
                    logger.warning(f"Missing or invalid bounding box for {field['type']}: {field['value']}")
                    continue

                # Convert normalized coordinates to pixel values
                x = int(bbox["Left"] * width)
                y = int(bbox["Top"] * height)
                w = int(bbox["Width"] * width)
                h = int(bbox["Height"] * height)

                # Validate coordinates
                if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
                    logger.warning(f"Invalid bounding box coordinates for {field['type']}: ({x}, {y}, {w}, {h})")
                    continue

                logger.debug(f"Masking {field['type']} at ({x}, {y}, {w}, {h}) with {mask_type}")
                if mask_type == "blur":
                    roi = image[y:y+h, x:x+w]
                    if roi.size == 0:
                        logger.warning(f"ROI empty for {field['type']} at ({x}, {y}, {w}, {h})")
                        continue
                    blurred = cv2.GaussianBlur(roi, (51, 51), 0)
                    image[y:y+h, x:x+w] = blurred
                else:  # Default to rectangle
                    cv2.rectangle(image, (x, y), (x+w, y+h), (0, 0, 0), -1)

                masked_fields += 1

            # Encode the masked image
            _, encoded_image = cv2.imencode(".png", image)
            logger.info(f"Masked {masked_fields} PII fields with {mask_type}")
            return encoded_image.tobytes()

        except Exception as e:
            logger.error(f"Masking error: {e}")
            raise Exception(f"Failed to mask image: {e}")