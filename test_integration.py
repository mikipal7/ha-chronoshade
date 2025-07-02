#!/usr/bin/env python3
"""Simple test script to validate the integration structure."""

import json
import sys
from pathlib import Path

def test_manifest():
    """Test manifest.json structure."""
    manifest_path = Path("custom_components/cover_time_based/manifest.json")
    
    if not manifest_path.exists():
        print("❌ manifest.json not found")
        return False
    
    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        required_keys = ["domain", "name", "version", "config_flow"]
        for key in required_keys:
            if key not in manifest:
                print(f"❌ Missing required key '{key}' in manifest.json")
                return False
        
        if manifest["config_flow"] is not True:
            print("❌ config_flow should be true in manifest.json")
            return False
        
        if manifest["integration_type"] != "device":
            print("❌ integration_type should be 'device' in manifest.json")
            return False
        
        print("✅ manifest.json is valid")
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in manifest.json: {e}")
        return False

def test_required_files():
    """Test that all required files exist."""
    required_files = [
        "custom_components/cover_time_based/__init__.py",
        "custom_components/cover_time_based/config_flow.py",
        "custom_components/cover_time_based/const.py",
        "custom_components/cover_time_based/cover.py",
        "custom_components/cover_time_based/strings.json",
        "custom_components/cover_time_based/translations/en.json",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            all_exist = False
    
    return all_exist

def test_strings_json():
    """Test strings.json structure."""
    strings_path = Path("custom_components/cover_time_based/strings.json")
    
    if not strings_path.exists():
        print("❌ strings.json not found")
        return False
    
    try:
        with open(strings_path) as f:
            strings = json.load(f)
        
        if "config" not in strings:
            print("❌ Missing 'config' section in strings.json")
            return False
        
        if "step" not in strings["config"]:
            print("❌ Missing 'config.step' section in strings.json")
            return False
        
        if "user" not in strings["config"]["step"]:
            print("❌ Missing 'config.step.user' section in strings.json")
            return False
        
        print("✅ strings.json structure is valid")
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in strings.json: {e}")
        return False

def test_imports():
    """Test that Python files can be imported without syntax errors."""
    try:
        # Test basic syntax by compiling
        files_to_test = [
            "custom_components/cover_time_based/__init__.py",
            "custom_components/cover_time_based/config_flow.py",
            "custom_components/cover_time_based/const.py",
            "custom_components/cover_time_based/cover.py",
        ]
        
        for file_path in files_to_test:
            path = Path(file_path)
            if path.exists():
                with open(path) as f:
                    compile(f.read(), file_path, 'exec')
                print(f"✅ {file_path} syntax is valid")
            else:
                print(f"❌ {file_path} not found for syntax check")
                return False
        
        return True
    
    except SyntaxError as e:
        print(f"❌ Syntax error in {e.filename}: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Cover Time Based Integration")
    print("=" * 50)
    
    tests = [
        ("Manifest validation", test_manifest),
        ("Required files", test_required_files),
        ("Strings.json structure", test_strings_json),
        ("Python syntax", test_imports),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        if not test_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Integration structure looks good.")
        print("\n📝 Next steps:")
        print("1. Restart Home Assistant")
        print("2. Go to Settings > Devices & Services")
        print("3. Click 'Add Integration'")
        print("4. Search for 'Cover Time Based'")
        print("5. Configure your cover with the UI")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()