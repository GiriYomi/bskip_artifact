#!/usr/bin/env python3
"""
Test script to validate ablation study setup
Performs basic checks without running full benchmarks
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from run_ablation_study import AblationStudy


def test_setup():
    """Test that all prerequisites are in place"""
    print("=" * 80)
    print("ABLATION STUDY SETUP TEST")
    print("=" * 80)
    
    # Create a study instance
    study = AblationStudy(num_runs=1)  # Just 1 run for testing
    
    # Test prerequisites
    print("\nTesting prerequisites...")
    if not study.check_prerequisites():
        print("\n✗ Prerequisites check failed!")
        return False
    
    print("\n✓ Prerequisites check passed!")
    
    # Test version files
    print("\nVerifying version files...")
    for version in study.versions:
        version_file = version["file"]
        if not version_file.exists():
            print(f"  ✗ {version['id']}: {version_file} - NOT FOUND")
            return False
        
        # Check file is not empty
        size = version_file.stat().st_size
        if size == 0:
            print(f"  ✗ {version['id']}: File is empty")
            return False
        
        print(f"  ✓ {version['id']}: {version['name']} ({size:,} bytes)")
    
    print("\n✓ All version files verified!")
    
    # Test backup mechanism
    print("\nTesting backup mechanism...")
    original_file = study.bskiplist_dir / "bskip.h"
    backup_file = study.bskiplist_dir / "bskip_original_backup.h"
    
    # Check original exists
    if not original_file.exists():
        print(f"  ✗ Original bskip.h not found: {original_file}")
        return False
    
    print(f"  ✓ Original file found: {original_file}")
    
    # Test backup creation
    study.backup_original_bskip()
    if not backup_file.exists():
        print(f"  ✗ Backup creation failed")
        return False
    
    print(f"  ✓ Backup created: {backup_file}")
    
    # Test version switching
    print("\nTesting version switching...")
    test_version = study.versions[1]  # Try v1_binary_search
    print(f"  Testing switch to: {test_version['name']}")
    
    # Save original content
    with open(original_file, 'r') as f:
        original_content = f.read()
    
    # Switch to test version
    study.switch_to_version(test_version["file"])
    
    # Verify switch
    with open(original_file, 'r') as f:
        switched_content = f.read()
    
    if switched_content == original_content:
        print(f"  ✗ Version switch didn't change file")
        study.restore_original_bskip()
        return False
    
    print(f"  ✓ Successfully switched to {test_version['name']}")
    
    # Restore original
    study.restore_original_bskip()
    
    # Verify restoration
    with open(original_file, 'r') as f:
        restored_content = f.read()
    
    if restored_content != original_content:
        print(f"  ✗ Restoration failed - content differs")
        return False
    
    print(f"  ✓ Successfully restored original")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS PASSED!")
    print("=" * 80)
    print("\nYour ablation study setup is ready!")
    print("\nNext steps:")
    print("  1. Ensure dataset files are available")
    print("  2. Run: python3 run_ablation_study.py")
    print("  3. Or test with fewer runs: python3 run_ablation_study.py -n 3")
    print("=" * 80 + "\n")
    
    return True


if __name__ == '__main__':
    success = test_setup()
    sys.exit(0 if success else 1)




