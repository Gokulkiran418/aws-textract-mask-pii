import re
from loguru import logger
from typing import List, Dict
from langdetect import detect, DetectorFactory

# Ensure consistent language detection results
DetectorFactory.seed = 0

class PIIDetector:
    # Multilingual mapping of PII types to possible key aliases
    PII_KEY_MAPPING = {
        "Name": {
            "en": ["name", "full name", "fullname", "given name"],
            "ta": ["பெயர்", "முழு பெயர்", "ஸ்ரீராம்", "மாமுண்டி"],
            "hi": ["नाम", "पूरा नाम"]
        },
        "Address": {
            "en": ["address", "addr", "permanent address"],
            "ta": ["முகவரி"],
            "hi": ["पता"]
        },
        "Phone Number": {
            "en": ["phone", "mobile", "telephone", "contact number"],
            "ta": ["தொலைபேசி", "மொபைல்"],
            "hi": ["फोन", "मोबाइल"]
        },
        "Email Address": {
            "en": ["email", "e-mail", "mail"],
            "ta": ["மின்னஞ்சல்"],
            "hi": ["ईमेल"]
        },
        "Aadhaar Number": {
            "en": ["aadhaar number", "uid", "aadhaar"],
            "ta": ["ஆதார் எண்"],
            "hi": ["आधार संख्या"]
        },
        "Date of Birth": {
            "en": ["dob", "date of birth", "birth date", "bdate"],
            "ta": ["பிறந்த தேதி"],
            "hi": ["जन्म तिथி"]
        },
        "Gender": {
            "en": ["gender", "sex", "Male", "Female", "male", "female", "MALE", "FEMALE"],
            "ta": ["பாலினம்", "ஆண்", "பெண்"],
            "hi": ["लिंग", "पुरुष", "महिला"]
        },
    }

    # Regex patterns for fallback detection (multilingual)
    REGEX_PATTERNS = {
        "Name": {
            "en": r"^[A-Za-z]+(?:[\s-][A-Za-z]+)*$",  # Allows multiple words with spaces/hyphens
            "ta": r"^[\u0B80-\u0BFF]+(?:[\s-][\u0B80-\u0BFF]+)*$",  # Flexible Tamil name matching
            "hi": r"^[\u0900-\u097F]+(?:[\s-][\u0900-\u097F]+)*$"  # Flexible Hindi name matching
        },
        "Address": {
            "en": r"^\d{1,5}\s\w+\s\w+",
            "ta": r"^\d{1,5}\s[\u0B80-\u0BFF]+",
            "hi": r"^\d{1,5}\s[\u0900-\u097F]+"
        },
        "Phone Number": r"\b[789]\d{9}\b|\b[0-9]{3}-[0-9]{3}-[0-9]{4}\b|\b[0-9]{10}\b",  # Word boundaries
        "Email Address": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}",  # Non-anchored for flexibility
        "Aadhaar Number": r"\b\d{4}\s?\d{4}\s?\d{4}\b|\b\d{12}\b",  # Word boundaries
        "Date of Birth": r"\b\d{2}[-/]\d{2}[-/]\d{2,4}\b",  # Word boundaries
        "Gender": {
            "en": r"(?:^|\s)(male|female|Male|Female|MALE|FEMALE)(?:\s|$)",  # Matches within text
            "ta": r"(?:^|\s)(ஆண்|பெண்)(?:\s|$)",
            "hi": r"(?:^|\s)(पुरुष|महिला)(?:\s|$)"
        },
    }

    # Multilingual non-PII blacklist
    NON_PII_BLACKLIST = {
        "en": ["government", "india", "ministry", "department", "authority", "office", "official", "public", "state", "national", "federal", "bureau", "agency", "registry", "certificate", "document", "form", "application", "issued", "valid", "expired", "signature", "seal", "aadhaar", "colony", "space"],
        "ta": ["அரசு", "இந்தியா", "துறை", "அதிகாரம்", "அலுவலகம்", "பொது", "மாநில", "தேசிய", "ஆணை", "சான்றிதழ்", "ஆவணம்", "விண்ணப்பம்", "வழங்கப்பட்டது", "செல்லுபடியாகும்", "காலாவதியானது", "கையொப்பம்", "முத்திரை", "ஆதார்", "காலனி", "விண்வெளி"],
        "hi": ["सरकार", "भारत", "मंत्रालय", "विभाग", "प्राधिकरण", "कार्यालय", "आधिकारिक", "सार्वजनिक", "राज्य", "राष्ट्रीय", "संघीय", "ब्यूरो", "एजेंसी", "रजिस्ट्री", "प्रमाणपत्र", "दस्तावेज़", "फॉर्म", "आवेदन", "जारी", "मान्य", "समाप्त", "हस्ताक्षर", "मुहर", "आधार", "कॉलोनी", "अंतरिक्ष", "भारत सरकार"]
    }

    def detect_pii(self, textract_blocks: List[Dict], tesseract_lines: List[Dict]) -> List[Dict]:
        """Detect PII from Textract blocks and Tesseract lines with bounding boxes."""
        pii_fields = []
        key_value_pairs = self._extract_key_value_pairs(textract_blocks)
        logger.info(f"Extracted key-value pairs: {key_value_pairs}")

        seen_values = set()

        # 1. Key-based detection from Textract blocks
        for key, value in key_value_pairs.items():
            normalized_key = re.sub(r'[:\s]+$', '', key.lower().strip())
            pii_type = self._map_to_pii_type(normalized_key)
            if pii_type and value["text"] not in seen_values and not self._is_non_pii(value["text"]):
                pii_fields.append(self._build_field(pii_type, value))
                logger.debug(f"Mapped key '{key}' → {pii_type}")
                seen_values.add(value["text"])

        # 2. Regex fallback for Textract key-value pairs
        for key, value in key_value_pairs.items():
            if value["text"] in seen_values or self._is_non_pii(value["text"]):
                continue
            lang = self._detect_language(value["text"])
            for pii_type, pattern in self.REGEX_PATTERNS.items():
                if isinstance(pattern, dict):
                    pattern = pattern.get(lang, pattern.get("en", ""))
                if re.search(pattern, value["text"].strip()):  # Changed from re.match to re.search
                    pii_fields.append(self._build_field(pii_type, value))
                    logger.debug(f"Regex-matched '{value['text']}' → {pii_type}")
                    seen_values.add(value["text"])
                    break

        # 3. Standalone line blocks from Textract
        for block in textract_blocks:
            if block.get("BlockType") != "LINE" or not block.get("Text", "").strip():
                continue
            text = block["Text"].strip()
            if text in seen_values or self._is_non_pii(text):
                continue
            lang = self._detect_language(text)
            cleaned = re.sub(r'\D', '', text)
            pii_type = None
            if len(cleaned) == 10 and cleaned[0] in "789":
                pii_type = "Phone Number"
            elif re.search(self.REGEX_PATTERNS["Aadhaar Number"], text):
                pii_type = "Aadhaar Number"
            elif re.search(self.REGEX_PATTERNS["Email Address"], text):
                pii_type = "Email Address"
            elif re.search(self.REGEX_PATTERNS["Date of Birth"], text):
                pii_type = "Date of Birth"
            elif re.search(self.REGEX_PATTERNS["Gender"].get(lang, self.REGEX_PATTERNS["Gender"]["en"]), text):
                pii_type = "Gender"
            elif re.search(self.REGEX_PATTERNS["Name"].get(lang, self.REGEX_PATTERNS["Name"]["en"]), text):
                pii_type = "Name"
            if pii_type:
                field = {
                    "type": pii_type,
                    "value": text,
                    "bounding_box": block.get("Geometry", {}).get("BoundingBox", {}),
                    "confidence": block.get("Confidence", 0.0),
                }
                pii_fields.append(field)
                logger.debug(f"Standalone matched (Textract) '{text}' → {pii_type}")
                seen_values.add(text)

        # 4. Process Tesseract lines with bounding boxes and hybrid fallback
        for line in tesseract_lines:
            text = line["text"].strip()
            if not text or text in seen_values or self._is_non_pii(text):
                continue
            lang = self._detect_language(text)
            cleaned = re.sub(r'\D', '', text)
            pii_type = None
            if len(cleaned) == 10 and cleaned[0] in "789":
                pii_type = "Phone Number"
            elif re.search(self.REGEX_PATTERNS["Aadhaar Number"], text):
                pii_type = "Aadhaar Number"
            elif re.search(self.REGEX_PATTERNS["Email Address"], text):
                pii_type = "Email Address"
            elif re.search(self.REGEX_PATTERNS["Date of Birth"], text):
                pii_type = "Date of Birth"
            elif re.search(self.REGEX_PATTERNS["Gender"].get(lang, self.REGEX_PATTERNS["Gender"]["en"]), text):
                pii_type = "Gender"
            elif re.search(self.REGEX_PATTERNS["Name"].get(lang, self.REGEX_PATTERNS["Name"]["en"]), text):
                pii_type = "Name"

            if pii_type:
                # Hybrid fallback: Use Textract bounding box if text matches a Textract block
                bounding_box = line.get("bounding_box", {})
                confidence = line.get("confidence", 0.0)
                for block in textract_blocks:
                    if block.get("BlockType") == "LINE" and block.get("Text", "").strip() == text:
                        bounding_box = block.get("Geometry", {}).get("BoundingBox", bounding_box)
                        confidence = block.get("Confidence", confidence)
                        break
                field = {
                    "type": pii_type,
                    "value": text,
                    "bounding_box": bounding_box,
                    "confidence": confidence,
                }
                pii_fields.append(field)
                logger.debug(f"Standalone matched (Tesseract) '{text}' → {pii_type} with bounding_box: {bounding_box}")
                seen_values.add(text)

        logger.info(f"Detected PII fields: {len(pii_fields)}")
        return pii_fields

    def _extract_key_value_pairs(self, blocks: List[Dict]) -> Dict:
        pairs = {}
        keys = {}
        values = {}

        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block["EntityTypes"]:
                key_text = self._get_block_text(block, blocks).lower()
                keys[block["Id"]] = key_text
            elif block["BlockType"] == "KEY_VALUE_SET" and "VALUE" in block["EntityTypes"]:
                value_text = self._get_block_text(block, blocks)
                values[block["Id"]] = {
                    "text": value_text,
                    "bounding_box": block.get("Geometry", {}).get("BoundingBox", {}),
                    "confidence": block.get("Confidence", 0.0),
                }

        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block["EntityTypes"] and "Relationships" in block:
                for rel in block["Relationships"]:
                    if rel["Type"] == "VALUE":
                        for value_id in rel["Ids"]:
                            if value_id in values:
                                pairs[keys.get(block["Id"], "")] = values[value_id]
        return pairs

    def _get_block_text(self, block: Dict, all_blocks: List[Dict]) -> str:
        text = ""
        if "Relationships" in block:
            for rel in block["Relationships"]:
                if rel["Type"] == "CHILD":
                    for child_id in rel["Ids"]:
                        for b in all_blocks:
                            if b["Id"] == child_id and b["BlockType"] == "WORD":
                                text += b["Text"] + " "
        return text.strip()

    def _map_to_pii_type(self, key: str) -> str:
        for pii_type, lang_aliases in self.PII_KEY_MAPPING.items():
            for lang, aliases in lang_aliases.items():
                if any(alias.lower().strip() == key for alias in aliases):
                    return pii_type
        return None

    def _is_non_pii(self, text: str) -> bool:
        lang = self._detect_language(text)
        if lang in self.NON_PII_BLACKLIST:
            return any(word.lower() in text.lower() for word in self.NON_PII_BLACKLIST[lang])
        return False

    def _detect_language(self, text: str) -> str:
        try:
            return detect(text)
        except:
            return "en"  # Default to English if detection fails

    def _build_field(self, pii_type: str, value: Dict) -> Dict:
        return {
            "type": pii_type,
            "value": value["text"],
            "bounding_box": value["bounding_box"],
            "confidence": value["confidence"],
        }