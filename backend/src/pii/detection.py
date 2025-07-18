import re
from loguru import logger
from typing import List, Dict

class PIIDetector:
    PII_KEY_MAPPING = {
        "Name": ["Name", "Full Name"],
        "Address": ["Address", "Permanent Address"],
        "Date of Birth": ["DOB", "Date of Birth"],
        "Aadhaar Number": ["Aadhaar Number", "UID"],
        "Phone Number": ["Phone", "Mobile Number"],
        "Email Address": ["Email"],
    }

    REGEX_PATTERNS = {
        "Aadhaar Number": r"\d{12}",
        "Phone Number": r"[789]\d{9}",
        "Date of Birth": r"\d{2}/\d{2}/\d{4}",
        "Email Address": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    }

    def detect_pii(self, blocks: List[Dict]) -> List[Dict]:
        pii_fields = []
        key_value_pairs = self._extract_key_value_pairs(blocks)
        
        for key, value in key_value_pairs.items():
            pii_type = self._map_to_pii_type(key)
            if pii_type:
                pii_fields.append({
                    "type": pii_type,
                    "value": value["text"],
                    "bounding_box": value["bounding_box"],
                    "confidence": value["confidence"],
                })
            else:
                # Fallback to regex for values not tied to keys
                for pii_type, pattern in self.REGEX_PATTERNS.items():
                    if re.match(pattern, value["text"]):
                        pii_fields.append({
                            "type": pii_type,
                            "value": value["text"],
                            "bounding_box": value["bounding_box"],
                            "confidence": value["confidence"],
                        })
        logger.info(f"Detected PII fields: {len(pii_fields)}")
        return pii_fields

    def _extract_key_value_pairs(self, blocks: List[Dict]) -> Dict:
        pairs = {}
        key_block = None
        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block["EntityTypes"]:
                key_block = block
            elif block["BlockType"] == "KEY_VALUE_SET" and "VALUE" in block["EntityTypes"]:
                if key_block and "Relationships" in key_block:
                    for rel in key_block["Relationships"]:
                        if rel["Type"] == "VALUE":
                            value_block_id = rel["Ids"][0]
                            if block["Id"] == value_block_id:
                                key_text = self._get_block_text(key_block, blocks)
                                value_text = self._get_block_text(block, blocks)
                                pairs[key_text] = {
                                    "text": value_text,
                                    "bounding_box": block.get("Geometry", {}).get("BoundingBox", {}),
                                    "confidence": block.get("Confidence", 0.0),
                                }
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
            if key in key_aliases:
                return pii_type
        return None