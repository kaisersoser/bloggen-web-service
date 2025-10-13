#!/usr/bin/env python3
"""
Audit Tracker Consolidation Script - Phase 1.2

This script migrates all imports to use the single EnhancedDatabaseAuditTracker
and prepares for deletion of duplicate implementations.

Files to DELETE after migration:
- core/audit_tracker.py (647 lines)
- core/refactored_audit_tracker.py (106 lines)
- bloggen/audit_tracker.py (301 lines)
- bloggen/simple_audit_tracker.py (238 lines)

File to KEEP:
- core/enhanced_audit_tracker.py (657 lines) - Most complete implementation
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Color codes for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'


class AuditTrackerMigration:
    """Handles migration of audit tracker imports"""
    
    def __init__(self, backend_src_path: str):
        self.backend_src = Path(backend_src_path)
        self.replacements = {
            # Old imports -> New import
            r'from core\.audit_tracker import DatabaseAuditTracker': 
                'from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker',
            r'from core\.audit_tracker import \*':
                'from core.enhanced_audit_tracker import *',
            r'from bloggen\.audit_tracker import DatabaseCostTracker':
                'from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker',
            r'from bloggen\.audit_tracker import \*':
                'from core.enhanced_audit_tracker import *',
            r'from core\.refactored_audit_tracker import DatabaseAuditTracker':
                'from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker',
            r'from core\.refactored_audit_tracker import RefactoredDatabaseAuditTracker':
                'from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker',
            r'from bloggen\.simple_audit_tracker import SimpleAuditTracker':
                'from core.enhanced_audit_tracker import EnhancedDatabaseAuditTracker',
                
            # Class name replacements
            r'\bDatabaseAuditTracker\b': 'EnhancedDatabaseAuditTracker',
            r'\bRefactoredDatabaseAuditTracker\b': 'EnhancedDatabaseAuditTracker',
            r'\bDatabaseCostTracker\b': 'EnhancedDatabaseAuditTracker',
            r'\bSimpleAuditTracker\b': 'EnhancedDatabaseAuditTracker',
        }
        
        self.files_modified = []
        self.files_with_issues = []
        
    def scan_for_imports(self) -> Dict[str, List[Tuple[int, str]]]:
        """Scan all Python files for audit tracker imports"""
        print(f"\n{BLUE}Scanning for audit tracker imports...{RESET}")
        
        results = {}
        
        for py_file in self.backend_src.rglob("*.py"):
            if '__pycache__' in str(py_file):
                continue
                
            matches = []
            try:
                with open(py_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in self.replacements.keys():
                            if re.search(pattern, line):
                                matches.append((line_num, line.strip()))
                                
                if matches:
                    results[str(py_file)] = matches
            except Exception as e:
                print(f"{RED}Error reading {py_file}: {e}{RESET}")
                
        return results
    
    def migrate_file(self, filepath: str, dry_run: bool = True) -> Tuple[bool, int]:
        """Migrate a single file's imports"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            original_content = content
            changes_made = 0
            
            # Apply all replacements
            for pattern, replacement in self.replacements.items():
                new_content, count = re.subn(pattern, replacement, content)
                if count > 0:
                    content = new_content
                    changes_made += count
            
            # Check if content changed
            if content == original_content:
                return False, 0
            
            # Write changes if not dry run
            if not dry_run:
                with open(filepath, 'w') as f:
                    f.write(content)
                self.files_modified.append(filepath)
            
            return True, changes_made
            
        except Exception as e:
            print(f"{RED}Error migrating {filepath}: {e}{RESET}")
            self.files_with_issues.append((filepath, str(e)))
            return False, 0
    
    def verify_enhanced_tracker_exists(self) -> bool:
        """Verify the enhanced_audit_tracker.py file exists"""
        enhanced_path = self.backend_src / "core" / "enhanced_audit_tracker.py"
        
        if not enhanced_path.exists():
            print(f"{RED}ERROR: core/enhanced_audit_tracker.py does not exist!{RESET}")
            return False
        
        print(f"{GREEN}✓ core/enhanced_audit_tracker.py exists{RESET}")
        return True
    
    def generate_deletion_list(self) -> List[Path]:
        """Generate list of files to delete after migration"""
        files_to_delete = [
            self.backend_src / "core" / "audit_tracker.py",
            self.backend_src / "core" / "refactored_audit_tracker.py",
            self.backend_src / "bloggen" / "audit_tracker.py",
            self.backend_src / "bloggen" / "simple_audit_tracker.py",
        ]
        
        existing_files = [f for f in files_to_delete if f.exists()]
        return existing_files
    
    def run(self, dry_run: bool = True):
        """Run the migration process"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}AUDIT TRACKER CONSOLIDATION - Phase 1.2{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        
        if dry_run:
            print(f"{YELLOW}Running in DRY RUN mode (no files will be modified){RESET}\n")
        else:
            print(f"{RED}Running in LIVE mode (files WILL be modified){RESET}\n")
        
        # Step 1: Verify enhanced tracker exists
        if not self.verify_enhanced_tracker_exists():
            return False
        
        # Step 2: Scan for imports
        imports_found = self.scan_for_imports()
        
        if not imports_found:
            print(f"{GREEN}No old audit tracker imports found!{RESET}")
            return True
        
        print(f"\n{YELLOW}Found imports in {len(imports_found)} files:{RESET}")
        for filepath, matches in imports_found.items():
            rel_path = Path(filepath).relative_to(self.backend_src.parent)
            print(f"  {rel_path}: {len(matches)} match(es)")
        
        # Step 3: Migrate files
        print(f"\n{BLUE}Migrating files...{RESET}")
        
        total_changes = 0
        for filepath in imports_found.keys():
            changed, num_changes = self.migrate_file(filepath, dry_run)
            if changed:
                rel_path = Path(filepath).relative_to(self.backend_src.parent)
                status = "Would modify" if dry_run else "Modified"
                print(f"  {GREEN}✓{RESET} {status}: {rel_path} ({num_changes} change(s))")
                total_changes += num_changes
        
        # Step 4: Show deletion candidates
        print(f"\n{BLUE}Files ready for deletion after migration:{RESET}")
        files_to_delete = self.generate_deletion_list()
        
        total_lines = 0
        for filepath in files_to_delete:
            rel_path = filepath.relative_to(self.backend_src.parent)
            with open(filepath, 'r') as f:
                lines = len(f.readlines())
            total_lines += lines
            print(f"  {YELLOW}→{RESET} {rel_path} ({lines} lines)")
        
        # Summary
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Files to migrate: {len(imports_found)}")
        print(f"Total changes: {total_changes}")
        print(f"Files to delete: {len(files_to_delete)}")
        print(f"Lines to remove: {total_lines}")
        
        if self.files_with_issues:
            print(f"\n{RED}Issues encountered:{RESET}")
            for filepath, error in self.files_with_issues:
                print(f"  {filepath}: {error}")
        
        if dry_run:
            print(f"\n{YELLOW}This was a DRY RUN. No files were modified.{RESET}")
            print(f"{YELLOW}Run with --execute to apply changes.{RESET}")
        else:
            print(f"\n{GREEN}Migration complete! {len(self.files_modified)} files modified.{RESET}")
            print(f"\n{YELLOW}Next steps:{RESET}")
            print(f"  1. Run all tests: pytest backend/src/tests/")
            print(f"  2. If tests pass, delete old files: python migrate_audit_tracker.py --delete")
        
        return True


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate audit tracker imports')
    parser.add_argument('--execute', action='store_true', 
                       help='Execute migration (default is dry run)')
    parser.add_argument('--delete', action='store_true',
                       help='Delete old audit tracker files (use AFTER testing)')
    parser.add_argument('--backend-src', type=str,
                       default='backend/src',
                       help='Path to backend/src directory')
    
    args = parser.parse_args()
    
    # Get backend src path
    script_dir = Path(__file__).parent
    backend_src = script_dir / 'src'
    
    if not backend_src.exists():
        backend_src = Path(args.backend_src)
    
    if not backend_src.exists():
        print(f"{RED}ERROR: Backend src directory not found: {backend_src}{RESET}")
        print(f"Script location: {script_dir}")
        print(f"Looking for: {backend_src}")
        sys.exit(1)
    
    migrator = AuditTrackerMigration(str(backend_src))
    
    if args.delete:
        # Delete mode - remove old files
        print(f"\n{RED}WARNING: This will DELETE old audit tracker files!{RESET}")
        response = input("Are you sure? Type 'DELETE' to confirm: ")
        
        if response != 'DELETE':
            print("Cancelled.")
            sys.exit(0)
        
        files_to_delete = migrator.generate_deletion_list()
        for filepath in files_to_delete:
            try:
                filepath.unlink()
                print(f"{GREEN}✓ Deleted: {filepath.relative_to(backend_src.parent)}{RESET}")
            except Exception as e:
                print(f"{RED}✗ Failed to delete {filepath}: {e}{RESET}")
        
        print(f"\n{GREEN}Deletion complete!{RESET}")
    else:
        # Migration mode
        success = migrator.run(dry_run=not args.execute)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
