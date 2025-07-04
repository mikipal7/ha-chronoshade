#!/usr/bin/env python3
"""
ChronoShade Integration Verification Script
Verifies that the translation error is fixed and the integration is properly configured.
"""

import json
import os
import sys
from pathlib import Path

def check_translation_fix():
    """Check that the MALFORMED_ARGUMENT translation error is fixed."""
    print("🔍 Checking translation fix...")
    
    strings_path = Path("custom_components/chronoshade/strings.json")
    if not strings_path.exists():
        print("❌ strings.json not found!")
        return False
    
    try:
        with open(strings_path, 'r', encoding='utf-8') as f:
            strings_data = json.load(f)
        
        # Check user step description
        user_desc = strings_data.get('config', {}).get('step', {}).get('user', {}).get('description', '')
        
        # Look for the problematic placeholders
        if '{opening_example}' in user_desc or '{closing_example}' in user_desc:
            print("❌ Found unresolved placeholders that cause MALFORMED_ARGUMENT error!")
            print(f"   Found in: {user_desc[:100]}...")
            return False
        
        # Check that proper JSON examples are present
        if '{"0": 0, "10": 100}' in user_desc and '{"0": 100, "10": 0}' in user_desc:
            print("✅ Translation error fixed! JSON examples are properly embedded.")
        else:
            print("⚠️  JSON examples might not be properly formatted")
            return False
        
        # Check reconfigure step too
        reconfig_desc = strings_data.get('config', {}).get('step', {}).get('reconfigure', {}).get('description', '')
        if '{opening_example}' in reconfig_desc or '{closing_example}' in reconfig_desc:
            print("❌ Found unresolved placeholders in reconfigure step!")
            return False
        
        print("✅ All translation placeholders properly resolved!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in strings.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking strings.json: {e}")
        return False

def check_domain_consistency():
    """Check that all files use the new chronoshade domain consistently."""
    print("\n🔍 Checking domain consistency...")
    
    files_to_check = [
        ("custom_components/chronoshade/manifest.json", "domain", "chronoshade"),
        ("custom_components/chronoshade/const.py", "DOMAIN", "chronoshade"),
        ("hacs.json", "name", "ChronoShade"),
    ]
    
    all_good = True
    
    for file_path, key, expected_value in files_to_check:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            all_good = False
            continue
        
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if data.get(key) == expected_value:
                    print(f"✅ {file_path}: {key} = {expected_value}")
                else:
                    print(f"❌ {file_path}: {key} = {data.get(key)} (expected {expected_value})")
                    all_good = False
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if f'{key} = "{expected_value}"' in content:
                    print(f"✅ {file_path}: {key} = {expected_value}")
                else:
                    print(f"❌ {file_path}: Could not verify {key} = {expected_value}")
                    all_good = False
                    
        except Exception as e:
            print(f"❌ Error checking {file_path}: {e}")
            all_good = False
    
    return all_good

def check_file_structure():
    """Check that all required files exist."""
    print("\n🔍 Checking file structure...")
    
    required_files = [
        "custom_components/chronoshade/__init__.py",
        "custom_components/chronoshade/manifest.json",
        "custom_components/chronoshade/strings.json",
        "custom_components/chronoshade/config_flow.py",
        "custom_components/chronoshade/cover.py",
        "custom_components/chronoshade/const.py",
        "custom_components/chronoshade/services.yaml",
        "README.md",
        "CHANGELOG.md",
        "hacs.json",
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} required files!")
        return False
    else:
        print(f"\n✅ All {len(required_files)} required files present!")
        return True

def main():
    """Run all verification checks."""
    print("🚀 ChronoShade Integration Verification")
    print("=" * 50)
    
    checks = [
        ("Translation Fix", check_translation_fix),
        ("Domain Consistency", check_domain_consistency),
        ("File Structure", check_file_structure),
    ]
    
    passed = 0
    total = len(checks)
    
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}")
        print("-" * 30)
        if check_func():
            passed += 1
            print(f"✅ {check_name} - PASSED")
        else:
            print(f"❌ {check_name} - FAILED")
    
    print("\n" + "=" * 50)
    print(f"📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ChronoShade is ready for use!")
        print("   • Translation error (MALFORMED_ARGUMENT) is fixed")
        print("   • All files properly rebranded")
        print("   • Integration structure is correct")
        print("\nNext steps:")
        print("   1. Restart Home Assistant")
        print("   2. Add ChronoShade integration via UI")
        print("   3. Configure your covers")
        return 0
    else:
        print(f"\n❌ {total - passed} checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())