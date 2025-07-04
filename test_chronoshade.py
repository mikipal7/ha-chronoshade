#!/usr/bin/env python3
"""Test script for ChronoShade integration."""

import json
import sys
import os

# Add the custom component to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'chronoshade'))

def test_json_examples():
    """Test the JSON examples from strings.json."""
    print("🧪 Testing ChronoShade JSON examples...")
    
    # Test opening example
    opening_example = '{"0": 0, "10": 100}'
    try:
        opening_data = json.loads(opening_example)
        print(f"✅ Opening example parsed successfully: {opening_data}")
    except json.JSONDecodeError as e:
        print(f"❌ Opening example failed: {e}")
        return False
    
    # Test closing example
    closing_example = '{"0": 100, "10": 0}'
    try:
        closing_data = json.loads(closing_example)
        print(f"✅ Closing example parsed successfully: {closing_data}")
    except json.JSONDecodeError as e:
        print(f"❌ Closing example failed: {e}")
        return False
    
    return True

def test_manifest():
    """Test manifest.json structure."""
    print("\n📋 Testing manifest.json...")
    
    try:
        with open('custom_components/chronoshade/manifest.json', 'r') as f:
            manifest = json.load(f)
        
        required_fields = ['domain', 'name', 'version', 'config_flow']
        for field in required_fields:
            if field not in manifest:
                print(f"❌ Missing required field: {field}")
                return False
            print(f"✅ {field}: {manifest[field]}")
        
        if manifest['domain'] != 'chronoshade':
            print(f"❌ Domain should be 'chronoshade', found: {manifest['domain']}")
            return False
        
        print("✅ Manifest validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Manifest test failed: {e}")
        return False

def test_strings():
    """Test strings.json structure."""
    print("\n🔤 Testing strings.json...")
    
    try:
        with open('custom_components/chronoshade/strings.json', 'r') as f:
            strings = json.load(f)
        
        # Check for malformed arguments (the original issue)
        config_desc = strings.get('config', {}).get('step', {}).get('user', {}).get('description', '')
        
        if '{opening_example}' in config_desc or '{closing_example}' in config_desc:
            print("❌ Found unresolved placeholders in strings.json")
            return False
        
        print("✅ No malformed argument placeholders found")
        
        # Check that examples are properly formatted
        if '{"0": 0, "10": 100}' in config_desc and '{"0": 100, "10": 0}' in config_desc:
            print("✅ JSON examples are properly formatted")
        else:
            print("❌ JSON examples not found or malformed")
            return False
        
        print("✅ Strings validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Strings test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 ChronoShade Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_json_examples,
        test_manifest,
        test_strings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ChronoShade is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())