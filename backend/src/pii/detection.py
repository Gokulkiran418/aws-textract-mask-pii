import re
from loguru import logger
from typing import List, Dict

class PIIDetector:
    PII_KEY_MAPPING = {
        "Name": ["name", "full name", "fullname", "given name"],
        "Address": ["address", "addr", "permanent address"],
        "Phone Number": ["phone", "mobile", "telephone", "contact number"],
        "Email Address": ["email", "e-mail", "mail"],
        "Aadhaar Number": ["aadhaar number", "uid", "aadhaar"],
        "Date of Birth": ["dob", "date of birth", "birth date", "bdate"],
    }

    REGEX_PATTERNS = {
        "Name": r"^[A-Za-z]+ [A-Za-z]+",  # Two-word names
        "Address": r"^\d{1,5}\s\w+\s\w+",
        "Phone Number": r"^[789]\d{9}$|^[0-9]{3}-[0-9]{3}-[0-4}$|^[0-9]{10}$",
        "Email Address": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}$",
        "Aadhaar Number": r"^\d{4}\s?\d{4}\s?\d{4}$|^\d{12}$",
        "Date of Birth": r"^\d{2}[-/]\d{2}[-/]\d{2,4}$",
    }

    NON_PII_BLACKLIST = {
        "government", "india", "ministry", "department", "authority", "office",
        "official", "public", "state", "national", "federal", "bureau", "agency",
        "registry", "certificate", "document", "form", "application", "issued",
        "valid", "expired", "signature", "seal", "aadhaar", "colony", "space"
    }

    def detect_pii(self, blocks: List[Dict]) -> List[Dict]:
        pii_fields = []
        key_value_pairs = self._extract_key_value_pairs(blocks)
        logger.info(f"Extracted key-value pairs: {key_value_pairs}")

        seen_values = set()
        # 1. Key-based detection
        for key, value in key_value_pairs.items():
            normalized_key = re.sub(r'[:\s]+$', '', key.lower().strip())
            pii_type = self._map_to_pii_type(normalized_key)
            if pii_type and value["text"] not in seen_values and not self._is_non_pii(value["text"]):
                pii_fields.append(self._build_field(pii_type, value))
                seen_values.add(value["text"])

        # 2. Regex fallback
        for key, value in key_value_pairs.items():
            if value["text"] in seen_values or self._is_non_pii(value["text"]):
                continue
            for pii_type, pattern in self.REGEX_PATTERNS.items():
                if re.match(pattern, value["text"].strip()):
                    pii_fields.append(self._build_field(pii_type, value))
                    seen_values.add(value["text"])
                    break

        # 3. Standalone line blocks
        for block in blocks:
            text = block.get("Text", "").strip()
            if block["BlockType"] != "LINE" or not text or text in seen_values or self._is_non_pii(text):
                continue
            cleaned = re.sub(r'\D', '', text)
            if len(cleaned) == 10 and cleaned[0] in "789":
                pii_type = "Phone Number"
            elif len(cleaned) == 12:
                pii_type = "Aadhaar Number"
            elif re.match(self.REGEX_PATTERNS["Email Address"], text):
                pii_type = "Email Address"
            elif re.match(self.REGEX_PATTERNS["Date of Birth"], text):
                pii_type = "Date of Birth"
            elif re.match(self.REGEX_PATTERNS["Name"], text):
                pii_type = "Name"
            else:
                continue
            field = {
                "type": pii_type,
                "value": text,
                "bounding_box": block.get("Geometry", {}).get("BoundingBox", {}),
                "confidence": block.get("Confidence", 0.0),
            }
            pii_fields.append(field)
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
        for pii_type, key_aliases in self.PII_KEY_MAPPING.items():
            if any(alias.lower().strip() == key for alias in key_aliases):
                return pii_type
        return None

    def _is_non_pii(self, text: str) -> bool:
        return any(word.lower() in text.lower() for word in self.NON_PII_BLACKLIST)

    def _build_field(self, pii_type: str, value: Dict) -> Dict:
        return {
            "type": pii_type,
            "value": value["text"],
            "bounding_box": value["bounding_box"],
            "confidence": value["confidence"],
        }