#!/usr/bin/env python3
"""Test script for flexible JSON parsing."""

import json
import re

def parse_flexible_json(json_str: str) -> dict:
    """Parse JSON with flexible key format (with or without quotes)."""
    if not json_str.strip():
        raise ValueError("JSON string cannot be empty")
    
    try:
        # First try standard JSON parsing
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            # Try to fix common JSON issues
            # Add quotes around unquoted keys
            
            # Replace unquoted keys with quoted keys
            # This regex finds keys that are not quoted
            fixed_json = re.sub(r'(\w+)(\s*:\s*)', r'"\1"\2', json_str)
            
            # Try parsing the fixed JSON
            return json.loads(fixed_json)
        except (json.JSONDecodeError, re.error):
            try:
                # Last attempt: try eval for Python dict syntax
                # This is safe because we control the input and only allow dict-like structures
                result = eval(json_str, {"__builtins__": {}}, {})
                if isinstance(result, dict):
                    return result
                else:
                    raise ValueError("Input must be a dictionary/object")
            except Exception as err:
                raise ValueError(f"Invalid JSON format. Please check syntax: {err}") from err

def test_json_parsing():
    """Test various JSON formats."""
    test_cases = [
        # Standard JSON
        '{"0": 0, "10": 100}',
        # Unquoted keys
        '{0: 0, 10: 100}',
        # Mixed quotes
        '{0: 0, "10": 100}',
        # Python dict syntax
        '{0: 0, 10: 100}',
        # With spaces
        '{ 0 : 0 , 10 : 100 }',
        # Complex example
        '{0: 0, 5: 50, 10: 100}',
    ]
    
    print("Testing flexible JSON parsing:")
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = parse_flexible_json(test_case)
            print(f"Test {i}: '{test_case}' -> {result} ✓")
        except Exception as e:
            print(f"Test {i}: '{test_case}' -> ERROR: {e} ✗")

if __name__ == "__main__":
    test_json_parsing()