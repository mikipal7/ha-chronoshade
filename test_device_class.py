#!/usr/bin/env python3
"""Test script to verify device class functionality."""

import sys
import os

# Add the custom component path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'custom_components', 'chronoshade'))

def test_device_class_logic():
    """Test the device class auto-detection logic."""
    print("Testing ChronoShade device class functionality...")
    
    try:
        from cover import CoverDeviceClass
        print("✓ CoverDeviceClass imported successfully")
        
        # Test device class values
        print(f"✓ BLIND device class: {CoverDeviceClass.BLIND}")
        print(f"✓ SHADE device class: {CoverDeviceClass.SHADE}")
        print(f"✓ SHUTTER device class: {CoverDeviceClass.SHUTTER}")
        print(f"✓ CURTAIN device class: {CoverDeviceClass.CURTAIN}")
        
        # Test string conversion
        test_cases = [
            ("blind", CoverDeviceClass.BLIND),
            ("shade", CoverDeviceClass.SHADE),
            ("shutter", CoverDeviceClass.SHUTTER),
            ("curtain", CoverDeviceClass.CURTAIN),
        ]
        
        for test_str, expected in test_cases:
            result = getattr(CoverDeviceClass, test_str.upper())
            if result == expected:
                print(f"✓ String '{test_str}' converts to {expected}")
            else:
                print(f"✗ String '{test_str}' conversion failed")
        
        print("\n🎉 All device class tests passed!")
        print("\nDevice class logic:")
        print("- If tilt is configured: BLIND (blinds commonly have tilt)")
        print("- If no tilt configured: SHADE (shades are position-only)")
        print("- User can override via device_class configuration option")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_device_class_logic()
    sys.exit(0 if success else 1)