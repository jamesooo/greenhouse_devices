#!/usr/bin/env python3
"""
Generate a C header file from .env file entries.
Usage: python generate_env_header.py <input_env_file> <output_header_file>

Features:
- If .env doesn't exist, copies .env.default to .env
- Validates that all keys in .env.default exist in .env
- Warns and fills in missing values from .env.default
"""

import sys
import os
import re
import shutil
from pathlib import Path


def sanitize_key(key):
    """Convert environment variable name to valid C macro name."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^A-Z0-9_]', '_', key.upper())
    # Ensure it doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = '_' + sanitized
    return sanitized


def escape_c_string(value):
    """Escape a string value for use in C code."""
    # Escape backslashes and quotes
    value = value.replace('\\', '\\\\')
    value = value.replace('"', '\\"')
    value = value.replace('\n', '\\n')
    value = value.replace('\r', '\\r')
    value = value.replace('\t', '\\t')
    return value


def should_exclude_key(key):
    """
    Check if a key should be excluded from the generated header.
    Excludes backend/infrastructure keys not needed by ESP32 firmware.
    """
    exclude_prefixes = [
        'POSTGRES_',      # PostgreSQL database credentials
        'GF_SECURITY_',   # Grafana security settings
    ]
    
    for prefix in exclude_prefixes:
        if key.startswith(prefix):
            return True
    return False


def parse_env_file(env_file_path, apply_filter=True):
    """
    Parse .env file and return a dictionary of key-value pairs.
    
    Args:
        env_file_path: Path to the .env file
        apply_filter: If True, exclude keys matching exclusion patterns
    """
    env_vars = {}
    excluded_count = 0
    
    if not os.path.exists(env_file_path):
        return env_vars
    
    with open(env_file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            # Strip whitespace and skip empty lines or comments
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Check if key should be excluded
                if apply_filter and should_exclude_key(key):
                    excluded_count += 1
                    continue
                
                # Remove quotes if present
                if value and value[0] in ('"', "'") and value[-1] == value[0]:
                    value = value[1:-1]
                
                env_vars[key] = value
            else:
                print(f"Warning: Skipping malformed line {line_num}: {line}", file=sys.stderr)
    
    if apply_filter and excluded_count > 0:
        print(f"ℹ️  Excluded {excluded_count} backend/infrastructure variable(s)", file=sys.stderr)
    
    return env_vars


def ensure_env_file_exists(env_file, env_default_file):
    """
    Ensure .env file exists. If not, copy from .env.default.
    Returns True if .env was created, False if it already existed.
    """
    if not os.path.exists(env_file):
        if os.path.exists(env_default_file):
            print(f"⚠️  .env file not found. Creating from {env_default_file}", file=sys.stderr)
            shutil.copy2(env_default_file, env_file)
            print(f"✅ Created {env_file} from template", file=sys.stderr)
            return True
        else:
            print(f"❌ ERROR: Neither {env_file} nor {env_default_file} exist!", file=sys.stderr)
            print(f"   Please create {env_default_file} as a template.", file=sys.stderr)
            return False
    return False


def validate_and_merge_env(env_vars, env_default_vars, env_file):
    """
    Validate that all keys from .env.default exist in .env.
    If any are missing, warn and use values from .env.default.
    Returns the merged dictionary.
    
    Note: Only validates non-excluded keys (those that pass the filter).
    """
    merged = env_vars.copy()
    missing_keys = []
    
    for key, default_value in env_default_vars.items():
        # Skip excluded keys in validation
        if should_exclude_key(key):
            continue
            
        if key not in env_vars:
            missing_keys.append(key)
            merged[key] = default_value
    
    if missing_keys:
        print(f"\n⚠️  WARNING: Missing environment variables in {env_file}:", file=sys.stderr)
        for key in missing_keys:
            print(f"   - {key} (using value from .env.default)", file=sys.stderr)
        print(f"\n💡 Consider adding these to {env_file}:\n", file=sys.stderr)
        for key in missing_keys:
            print(f"   {key}={env_default_vars[key]}", file=sys.stderr)
        print(file=sys.stderr)
    
    return merged


def generate_header(env_vars, output_path):
    """Generate C header file from environment variables."""
    header_guard = "ENV_CONFIG_H"
    
    with open(output_path, 'w') as f:
        f.write("/**\n")
        f.write(" * @file env_config.h\n")
        f.write(" * @brief Auto-generated environment configuration\n")
        f.write(" * \n")
        f.write(" * This file is automatically generated from .env file.\n")
        f.write(" * DO NOT EDIT MANUALLY - changes will be overwritten.\n")
        f.write(" * \n")
        f.write(" * Note: Backend/infrastructure variables (POSTGRES_*, GF_SECURITY_*)\n")
        f.write(" * are automatically filtered out and not included in firmware.\n")
        f.write(" */\n\n")
        
        f.write(f"#ifndef {header_guard}\n")
        f.write(f"#define {header_guard}\n\n")
        
        f.write("#ifdef __cplusplus\n")
        f.write('extern "C" {\n')
        f.write("#endif\n\n")
        
        if env_vars:
            f.write("/* Environment variables */\n")
            for key, value in sorted(env_vars.items()):
                macro_name = sanitize_key(key)
                escaped_value = escape_c_string(value)
                f.write(f'#define ENV_{macro_name} "{escaped_value}"\n')
            f.write("\n")
        else:
            f.write("/* No environment variables defined */\n\n")
        
        f.write("#ifdef __cplusplus\n")
        f.write("}\n")
        f.write("#endif\n\n")
        
        f.write(f"#endif /* {header_guard} */\n")


def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <input_env_file> <output_header_file>", file=sys.stderr)
        sys.exit(1)
    
    env_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Determine .env.default path (same directory as .env)
    env_dir = os.path.dirname(env_file)
    env_default_file = os.path.join(env_dir, '.env.default')
    
    # Ensure .env exists (copy from .env.default if needed)
    was_created = ensure_env_file_exists(env_file, env_default_file)
    
    # Parse both files
    env_vars = parse_env_file(env_file)
    env_default_vars = parse_env_file(env_default_file)
    
    # Validate and merge (warn about missing keys)
    if env_default_vars and not was_created:
        # Only validate if we didn't just create .env from .env.default
        final_vars = validate_and_merge_env(env_vars, env_default_vars, env_file)
    else:
        final_vars = env_vars
    
    # Generate header file
    generate_header(final_vars, output_file)
    
    if final_vars:
        print(f"✅ Generated {output_file} with {len(final_vars)} environment variable(s)")
    else:
        print(f"⚠️  Generated {output_file} with no environment variables", file=sys.stderr)


if __name__ == "__main__":
    main()
