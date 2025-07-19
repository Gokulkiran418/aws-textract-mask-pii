from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from src.ocr.textract import TextractClient
from src.pii.detection import PIIDetector
from src.masking.image import ImageMasker
from loguru import logger
import base64

app = FastAPI(title="PII Masking API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Allow frontend origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.post("/upload")
async def upload_image(file: UploadFile = File(...), mask_type: str = "rectangle"):
    try:
        if file.content_type not in ["image/png", "image/jpeg"]:
            raise HTTPException(status_code=400, detail="Invalid image format. Use PNG or JPEG.")

        image_bytes = await file.read()
        logger.info(f"Received image upload: {file.filename}, mask_type: {mask_type}")

        # Extract text with Textract
        textract_client = TextractClient()
        blocks = await textract_client.analyze_document(image_bytes)

        # Extract text with Tesseract for Hindi and Tamil
        hindi_lines = textract_client.extract_text_with_tesseract(image_bytes, "hin")
        tamil_lines = textract_client.extract_text_with_tesseract(image_bytes, "tam")
        tesseract_lines = hindi_lines + tamil_lines
        logger.debug(f"Tesseract extracted lines: {len(tesseract_lines)}")

        # Detect PII
        pii_detector = PIIDetector()
        pii_fields = pii_detector.detect_pii(blocks, tesseract_lines)

        # Mask image
        masker = ImageMasker()
        masked_image_bytes = masker.mask_image(image_bytes, pii_fields, mask_type)

        # Encode as base64 for frontend
        encoded_image = base64.b64encode(masked_image_bytes).decode("utf-8")
        return {"masked_image": encoded_image}
    except Exception as e:
        logger.error(f"API error: {e}")
        raise HTTPException(status_code=500, detail=str(e))