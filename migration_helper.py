#!/usr/bin/env python3
"""
Migration helper script for Cover Time Based v3.0 to v4.0
Converts YAML configuration to UI configuration format.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

def extract_yaml_config(config_text: str) -> List[Dict[str, Any]]:
    """Extract cover_time_based configuration from YAML text."""
    covers = []
    
    # Look for cover_time_based platform configuration
    lines = config_text.split('\n')
    in_cover_section = False
    in_devices_section = False
    current_device = None
    current_device_config = {}
    indent_level = 0
    
    for line in lines:
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Calculate indentation
        line_indent = len(line) - len(line.lstrip())
        
        # Check for cover platform
        if 'platform: cover_time_based' in line:
            in_cover_section = True
            continue
        
        if in_cover_section:
            # Check for devices section
            if stripped.startswith('devices:'):
                in_devices_section = True
                indent_level = line_indent
                continue
            
            if in_devices_section:
                # New device
                if line_indent == indent_level + 2 and ':' in stripped and not stripped.startswith('-'):
                    # Save previous device
                    if current_device and current_device_config:
                        covers.append({
                            'device_id': current_device,
                            **current_device_config
                        })
                    
                    # Start new device
                    current_device = stripped.rstrip(':')
                    current_device_config = {}
                    continue
                
                # Device configuration
                if current_device and line_indent > indent_level + 2:
                    if ':' in stripped:
                        key, value = stripped.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Handle different value types
                        if key in ['opening_time_map', 'closing_time_map']:
                            # This is a time map - we'll need to parse it
                            current_device_config[key] = 'TIME_MAP_PLACEHOLDER'
                        elif value.lower() in ['true', 'false']:
                            current_device_config[key] = value.lower() == 'true'
                        elif value.replace('.', '').isdigit():
                            current_device_config[key] = float(value) if '.' in value else int(value)
                        else:
                            current_device_config[key] = value.strip('"\'')
                
                # End of devices section
                if line_indent <= indent_level and stripped and not stripped.startswith('devices'):
                    in_devices_section = False
                    in_cover_section = False
                    # Save last device
                    if current_device and current_device_config:
                        covers.append({
                            'device_id': current_device,
                            **current_device_config
                        })
                    break
    
    # Save last device if we reached end of file
    if current_device and current_device_config:
        covers.append({
            'device_id': current_device,
            **current_device_config
        })
    
    return covers

def parse_time_map_from_yaml(yaml_text: str, device_id: str, map_type: str) -> Dict[str, int]:
    """Parse time map from YAML text for a specific device."""
    lines = yaml_text.split('\n')
    in_device = False
    in_time_map = False
    time_map = {}
    
    for line in lines:
        stripped = line.strip()
        
        if f'{device_id}:' in line:
            in_device = True
            continue
        
        if in_device:
            if f'{map_type}:' in stripped:
                in_time_map = True
                continue
            
            if in_time_map:
                # Check if we're still in the time map (indented)
                if line.startswith('        ') or line.startswith('\t\t'):
                    if ':' in stripped:
                        try:
                            key, value = stripped.split(':', 1)
                            time_key = key.strip()
                            time_value = int(value.strip())
                            time_map[time_key] = time_value
                        except ValueError:
                            continue
                else:
                    # End of time map
                    break
    
    return time_map

def convert_to_ui_format(covers: List[Dict[str, Any]], yaml_text: str) -> List[Dict[str, Any]]:
    """Convert YAML format to UI configuration format."""
    ui_configs = []
    
    for cover in covers:
        device_id = cover.get('device_id', '')
        
        # Parse time maps from YAML
        opening_time_map = parse_time_map_from_yaml(yaml_text, device_id, 'opening_time_map')
        closing_time_map = parse_time_map_from_yaml(yaml_text, device_id, 'closing_time_map')
        
        ui_config = {
            'name': cover.get('name', device_id),
            'open_switch_entity_id': cover.get('open_switch_entity_id', ''),
            'close_switch_entity_id': cover.get('close_switch_entity_id', ''),
            'stop_switch_entity_id': cover.get('stop_switch_entity_id', ''),
            'is_button': cover.get('is_button', False),
            'opening_time_map': json.dumps(opening_time_map) if opening_time_map else '{"0": 0, "10": 100}',
            'closing_time_map': json.dumps(closing_time_map) if closing_time_map else '{"0": 100, "10": 0}',
            'tilting_time_down': cover.get('tilting_time_down'),
            'tilting_time_up': cover.get('tilting_time_up'),
        }
        
        # Remove None values
        ui_config = {k: v for k, v in ui_config.items() if v is not None and v != ''}
        
        ui_configs.append(ui_config)
    
    return ui_configs

def print_ui_instructions(ui_configs: List[Dict[str, Any]]):
    """Print instructions for UI configuration."""
    print("🎉 Migration Helper - Cover Time Based v3.0 → v4.0")
    print("=" * 60)
    
    if not ui_configs:
        print("❌ No cover_time_based configurations found in the provided text.")
        print("\nMake sure you've copied the correct section from your configuration.yaml")
        return
    
    print(f"✅ Found {len(ui_configs)} cover(s) to migrate")
    print("\n📋 UI Configuration Instructions:")
    print("1. Go to Settings > Devices & Services")
    print("2. Click 'Add Integration'")
    print("3. Search for 'Cover Time Based'")
    print("4. For each cover below, add a new integration entry:")
    
    for i, config in enumerate(ui_configs, 1):
        print(f"\n🏠 Cover {i}: {config['name']}")
        print("-" * 40)
        
        for key, value in config.items():
            if key == 'name':
                print(f"Name: {value}")
            elif key == 'open_switch_entity_id':
                print(f"Open Switch Entity: {value}")
            elif key == 'close_switch_entity_id':
                print(f"Close Switch Entity: {value}")
            elif key == 'stop_switch_entity_id':
                print(f"Stop Switch Entity: {value}")
            elif key == 'is_button':
                print(f"Switches are buttons: {'Yes' if value else 'No'}")
            elif key == 'opening_time_map':
                print(f"Opening Time Map: {value}")
            elif key == 'closing_time_map':
                print(f"Closing Time Map: {value}")
            elif key == 'tilting_time_down':
                print(f"Tilt Down Time: {value}")
            elif key == 'tilting_time_up':
                print(f"Tilt Up Time: {value}")
    
    print("\n" + "=" * 60)
    print("⚠️  After configuring through UI:")
    print("1. Remove the YAML configuration from configuration.yaml")
    print("2. Restart Home Assistant")
    print("3. Test that your covers work correctly")
    
    print("\n💾 Backup Recommendation:")
    print("Keep a backup of your YAML configuration until you've")
    print("verified everything works with the new UI configuration.")

def main():
    """Main migration helper function."""
    print("Cover Time Based Migration Helper")
    print("Paste your YAML configuration below (Ctrl+D or Ctrl+Z when done):")
    print("-" * 50)
    
    try:
        # Read YAML configuration from stdin
        yaml_content = sys.stdin.read()
        
        if not yaml_content.strip():
            print("❌ No configuration provided.")
            return
        
        # Extract and convert configuration
        covers = extract_yaml_config(yaml_content)
        ui_configs = convert_to_ui_format(covers, yaml_content)
        
        # Print instructions
        print_ui_instructions(ui_configs)
        
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled.")
    except Exception as e:
        print(f"\n❌ Error processing configuration: {e}")
        print("Please check your YAML format and try again.")

if __name__ == "__main__":
    main()