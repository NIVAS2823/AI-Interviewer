# fix_pydantic_v2.py
"""
Fix Pydantic v2 warnings by updating Config settings
Run: python fix_pydantic_v2.py
"""
import os
import re

def fix_pydantic_config(file_path):
    """Replace old Pydantic v1 config with v2 syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace allow_population_by_field_name with populate_by_name
        content = content.replace(
            'allow_population_by_field_name',
            'populate_by_name'
        )
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Fix all Python files in app/ directory"""
    print("="*70)
    print("🔧 Fixing Pydantic v2 Configuration")
    print("="*70)
    
    fixed_files = []
    
    # Walk through app directory
    for root, dirs, files in os.walk("app"):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_pydantic_config(file_path):
                    fixed_files.append(file_path)
                    print(f"✅ Fixed: {file_path}")
    
    print("\n" + "="*70)
    if fixed_files:
        print(f"🎉 Fixed {len(fixed_files)} file(s)")
        for f in fixed_files:
            print(f"   - {f}")
    else:
        print("✅ No files needed fixing (already v2 compliant)")
    print("="*70)

if __name__ == "__main__":
    main()