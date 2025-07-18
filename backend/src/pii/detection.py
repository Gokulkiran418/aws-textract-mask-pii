import re
from loguru import logger
from typing import List, Dict

class PIIDetector:
    # Mapping of PII types to possible key aliases (case-insensitive)
    PII_KEY_MAPPING = {
        "Name": ["name", "full name", "fullname", "given name"],
        "Address": ["address", "addr", "permanent address"],
        "Phone Number": ["phone", "mobile", "telephone", "contact number"],
        "Email Address": ["email", "e-mail", "mail"],
        "Aadhaar Number": ["aadhaar number", "uid", "aadhaar"],
        "Date of Birth": ["dob", "date of birth", "birth date", "bdate"],
    }

    # Regex patterns for fallback detection with exclusivity checks
    REGEX_PATTERNS = {
        "Name": r"^[A-Za-z][A-Za-z\s'-]{1,}$",  # Start with letter, no @ to avoid emails
        "Address": r"^\d{1,5}\s\w+\s\w+",  # e.g., "8a youland street"
        "Phone Number": r"^[789]\d{9}$|^[0-9]{3}-[0-9]{3}-[0-9]{4}$|^[0-9]{10}$",  # Indian/US formats
        "Email Address": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "Aadhaar Number": r"^\d{4}\s?\d{4}\s?\d{4}$|^\d{12}$",  # 12 digits or spaced format
        "Date of Birth": r"^\d{2}[-/]\d{2}[-/]\d{2,4}$",  # e.g., "21-05-12" or "21/05/2012"
    }

    def detect_pii(self, blocks: List[Dict]) -> List[Dict]:
        """Detect PII fields in Textract blocks and return them for masking."""
        pii_fields = []
        key_value_pairs = self._extract_key_value_pairs(blocks)
        logger.info(f"Extracted key-value pairs: {key_value_pairs}")

        # Process key-value pairs with priority on mapping
        seen_values = set()  # To prevent duplicate bounding box assignments
        for key, value in key_value_pairs.items():
            normalized_key = re.sub(r'[:\s]+$', '', key.lower().strip())  # Remove colons and trailing spaces
            pii_type = self._map_to_pii_type(normalized_key)
            if pii_type and value["text"] not in seen_values:
                pii_fields.append({
                    "type": pii_type,
                    "value": value["text"],
                    "bounding_box": value["bounding_box"],
                    "confidence": value["confidence"],
                })
                logger.debug(f"Mapped '{key}' to {pii_type}")
                seen_values.add(value["text"])

        # Regex fallback for unmapped key-value pairs
        for key, value in key_value_pairs.items():
            if value["text"] not in seen_values:
                for pii_type, pattern in self.REGEX_PATTERNS.items():
                    if re.match(pattern, value["text"].strip()) and not any(
                        re.match(self.REGEX_PATTERNS.get(other_type, r"^$"), value["text"].strip())
                        for other_type in self.REGEX_PATTERNS if other_type != pii_type
                    ):
                        pii_fields.append({
                            "type": pii_type,
                            "value": value["text"],
                            "bounding_box": value["bounding_box"],
                            "confidence": value["confidence"],
                        })
                        logger.debug(f"Matched '{value['text']}' to {pii_type} via regex")
                        seen_values.add(value["text"])
                        break  # Exit after first match to avoid overlap

        # Check standalone LINE blocks for PII
        for block in blocks:
            if block["BlockType"] == "LINE" and block.get("Text") and block.get("Text").strip() not in seen_values:
                text = block.get("Text", "").strip()
                cleaned = self.clean_text(text)
                if len(cleaned) == 10 and cleaned[0] in '789':
                    pii_type = "Phone Number"
                elif len(cleaned) == 12:
                    pii_type = "Aadhaar Number"
                elif re.match(self.REGEX_PATTERNS["Email Address"], text):
                    pii_type = "Email Address"
                elif re.match(self.REGEX_PATTERNS["Date of Birth"], text):
                    pii_type = "Date of Birth"
                else:
                    continue
                bounding_box = block.get("Geometry", {}).get("BoundingBox", {})
                confidence = block.get("Confidence", 0.0)
                pii_fields.append({
                    "type": pii_type,
                    "value": text,
                    "bounding_box": bounding_box,
                    "confidence": confidence,
                })
                logger.debug(f"Matched standalone '{text}' to {pii_type}")
                seen_values.add(text)

        logger.info(f"Detected PII fields: {len(pii_fields)}")
        return pii_fields

    def _extract_key_value_pairs(self, blocks: List[Dict]) -> Dict:
        """Extract and normalize key-value pairs from Textract blocks."""
        pairs = {}
        keys = {}
        values = {}

        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block["EntityTypes"]:
                key_text = self._get_block_text(block, blocks).lower()
                keys[block["Id"]] = key_text
                logger.debug(f"Registered key ID {block['Id']} as '{key_text}'")
            elif block["BlockType"] == "KEY_VALUE_SET" and "VALUE" in block["EntityTypes"]:
                value_text = self._get_block_text(block, blocks)
                values[block["Id"]] = {
                    "text": value_text,
                    "bounding_box": block.get("Geometry", {}).get("BoundingBox", {}),
                    "confidence": block.get("Confidence", 0.0),
                }
                logger.debug(f"Registered value ID {block['Id']} as '{value_text}'")

        for block in blocks:
            if block["BlockType"] == "KEY_VALUE_SET" and "KEY" in block["EntityTypes"] and "Relationships" in block:
                for rel in block["Relationships"]:
                    if rel["Type"] == "VALUE":
                        for value_id in rel["Ids"]:
                            if value_id in values:
                                pairs[keys.get(block["Id"], "")] = values[value_id]
                                logger.debug(f"Paired key '{keys.get(block['Id'], '')}' with value '{values[value_id]['text']}'")
        return pairs

    def _get_block_text(self, block: Dict, all_blocks: List[Dict]) -> str:
        """Extract text from a block by aggregating its child WORD blocks."""
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
        """Map a normalized key to a PII type based on aliases."""
        for pii_type, key_aliases in self.PII_KEY_MAPPING.items():
            if any(alias.lower().strip() == key for alias in key_aliases):
                return pii_type
        return None

    def clean_text(self, text: str) -> str:
        """Remove non-digit characters for number-based PII detection."""
        return re.sub(r'\D', '', text)