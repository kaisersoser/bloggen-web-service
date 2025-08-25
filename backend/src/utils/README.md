# Backend Utilities

This directory contains utility scripts and tools for the backend application.

## Scripts

### `db_cleanup.py`
Database cleanup utility for dropping legacy tables and resetting data.
- **Purpose**: Drop unused tables, truncate active data tables
- **Safety**: Requires confirmation flags and supports dry-run mode
- **Usage**: 
  ```bash
  # Dry run
  DRY_RUN=1 RUN_DB_CLEANUP=confirm python src/utils/db_cleanup.py
  
  # Execute
  RUN_DB_CLEANUP=confirm python src/utils/db_cleanup.py
  ```

### `supabase_diagnostic.py`
Diagnostic tool for testing Supabase database connections and audit system.
- **Purpose**: Test database connectivity and verify audit system functionality
- **Usage**: `python src/utils/supabase_diagnostic.py`

### `normalize_phase_names.py`
Utility for normalizing phase names in the system.
- **Purpose**: Standardize phase naming conventions
- **Usage**: `python src/utils/normalize_phase_names.py`

### `toggle_image_generation.py`
Script for enabling/disabling AI image generation features.
- **Purpose**: Cost management by toggling image generation features
- **Usage**: `python src/utils/toggle_image_generation.py`

## Notes

- All utilities should be run from the backend root directory
- Most utilities require proper environment configuration
- Use dry-run modes when available for safety
