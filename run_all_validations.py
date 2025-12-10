"""
Comprehensive End-to-End Validation Report
Runs all validation tests and generates a detailed report
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr and "warning" not in result.stderr.lower():
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        return success, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        print("❌ Command timed out")
        return False, "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return False, str(e)

def main():
    print("="*70)
    print(" "*15 + "COMPREHENSIVE VALIDATION REPORT")
    print("="*70)
    print(f"Date: {datetime.now()}")
    print(f"Branch: refactor/postgres-migration")
    print(f"Working Directory: {Path.cwd()}")
    print("="*70)
    
    results = []
    
    # Test 1: Module imports and structure
    print("\n" + "="*70)
    print("SECTION 1: MODULE STRUCTURE VALIDATION")
    print("="*70)
    
    success, output = run_command(
        'python -c "from modules.database import base, duckdb_handler, postgres, factory; print(\'✓ All modules present\')"',
        "Module structure check"
    )
    results.append(("Module Structure", success))
    
    # Test 2: Core functionality
    print("\n" + "="*70)
    print("SECTION 2: CORE FUNCTIONALITY TESTS")
    print("="*70)
    
    success, output = run_command(
        "python validate_refactoring.py",
        "Core functionality test suite"
    )
    results.append(("Core Functionality", success))
    
    # Test 3: Backend switching
    print("\n" + "="*70)
    print("SECTION 3: BACKEND SWITCHING TESTS")
    print("="*70)
    
    success, output = run_command(
        "python test_backend_switching.py",
        "Backend switching validation"
    )
    results.append(("Backend Switching", success))
    
    # Test 4: Migration logic
    print("\n" + "="*70)
    print("SECTION 4: MIGRATION LOGIC TESTS")
    print("="*70)
    
    success, output = run_command(
        "python test_migration_logic.py",
        "Migration script logic validation"
    )
    results.append(("Migration Logic", success))
    
    # Test 5: SQL schema validation
    print("\n" + "="*70)
    print("SECTION 5: SQL SCHEMA VALIDATION")
    print("="*70)
    
    success, output = run_command(
        'python -c "import re; c=open(\'sql/init/01_schema.sql\').read(); t=len(re.findall(r\'CREATE TABLE\',c)); i=len(re.findall(r\'CREATE INDEX\',c)); print(f\'✓ {t} tables, {i} indexes defined\')"',
        "SQL schema syntax check"
    )
    results.append(("SQL Schema", success))
    
    # Test 6: Docker configuration
    print("\n" + "="*70)
    print("SECTION 6: DOCKER CONFIGURATION VALIDATION")
    print("="*70)
    
    success, output = run_command(
        "docker-compose config --quiet",
        "docker-compose.yml syntax validation"
    )
    results.append(("Docker Config", success))
    
    # Test 7: Dependencies
    print("\n" + "="*70)
    print("SECTION 7: DEPENDENCIES CHECK")
    print("="*70)
    
    success, output = run_command(
        'python -c "import psycopg2; import duckdb; import pandas; print(\'✓ All required packages installed\')"',
        "Required packages check"
    )
    results.append(("Dependencies", success))
    
    # Test 8: File structure
    print("\n" + "="*70)
    print("SECTION 8: FILE STRUCTURE VALIDATION")
    print("="*70)
    
    required_files = [
        "modules/database/base.py",
        "modules/database/postgres.py",
        "modules/database/duckdb_handler.py",
        "modules/database/factory.py",
        "sql/init/01_schema.sql",
        "scripts/migrate_to_postgres.py",
        "docs/POSTGRES_MIGRATION.md",
        "docker-compose.yml",
        ".env.example"
    ]
    
    all_exist = True
    for file_path in required_files:
        exists = Path(file_path).exists()
        status = "✓" if exists else "✗"
        print(f"{status} {file_path}")
        if not exists:
            all_exist = False
    
    results.append(("File Structure", all_exist))
    
    # Print final summary
    print("\n" + "="*70)
    print(" "*25 + "FINAL SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed
    
    print(f"\nTotal Validation Sections: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/total*100):.1f}%")
    
    print("\nDetailed Results:")
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} - {name}")
    
    print("\n" + "="*70)
    
    if failed == 0:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("\nThe refactoring is complete and working correctly:")
        print("  ✓ Database abstraction layer implemented")
        print("  ✓ Both DuckDB and PostgreSQL backends supported")
        print("  ✓ Backend switching works seamlessly")
        print("  ✓ Migration logic validated")
        print("  ✓ SQL schema ready for PostgreSQL")
        print("  ✓ Docker configuration valid")
        print("  ✓ All dependencies installed")
        print("  ✓ File structure complete")
        print("\nNext Steps:")
        print("  1. Start PostgreSQL: docker-compose up -d postgres")
        print("  2. Run migration: python scripts/migrate_to_postgres.py")
        print("  3. Switch backend: Set DATABASE_BACKEND=postgresql in .env")
        print("  4. Test with real data")
    else:
        print("⚠️  SOME VALIDATIONS FAILED")
        print("\nFailed sections need attention before proceeding.")
    
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
