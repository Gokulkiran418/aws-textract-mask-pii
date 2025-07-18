import pytest
from src.pii.detection import PIIDetector

def test_pii_detection():
    detector = PIIDetector()
    mock_blocks = [
        {
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["KEY"],
            "Text": "Name",
            "Relationships": [{"Type": "VALUE", "Ids": ["value1"]}],
        },
        {
            "BlockType": "KEY_VALUE_SET",
            "EntityTypes": ["VALUE"],
            "Id": "value1",
            "Text": "John Doe",
            "Geometry": {"BoundingBox": {"Left": 0.1, "Top": 0.1, "Width": 0.2, "Height": 0.1}},
            "Confidence": 0.99,
        },
        {
            "BlockType": "WORD",
            "Text": "John",
            "Id": "word1",
        },
        {
            "BlockType": "WORD",
            "Text": "Doe",
            "Id": "word2",
        },
    ]
    pii_fields = detector.detect_pii(mock_blocks)
    assert len(pii_fields) == 1
    assert pii_fields[0]["type"] == "Name"
    assert pii_fields[0]["value"] == "John Doe"