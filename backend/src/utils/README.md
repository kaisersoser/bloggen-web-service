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
- **Purpose**: Cost management by toggling image generation features on/off
- **Usage**: 
  ```bash
  # Disable AI image generation (free Unsplash only)
  python src/utils/toggle_image_generation.py disable
  
  # Enable AI image generation (uses configured provider)
  python src/utils/toggle_image_generation.py enable
  ```

### `switch_image_provider.py` ⭐ NEW
Script for switching between different AI image generation models and providers.
- **Purpose**: Easy model switching with automatic cost tracking updates
- **Supports**: 7 models across Replicate and OpenAI
- **Usage**:
  ```bash
  # List all available models
  python src/utils/switch_image_provider.py --list
  
  # Switch to Replicate Imagen-3-Fast (recommended default)
  python src/utils/switch_image_provider.py replicate imagen-3-fast
  
  # Switch to budget SDXL (96% cheaper than DALL-E 3!)
  python src/utils/switch_image_provider.py replicate sdxl
  
  # Switch to OpenAI DALL-E 3
  python src/utils/switch_image_provider.py openai dall-e-3
  ```
- **Documentation**: See `docs/IMAGE_PROVIDER_GUIDE.md` for comprehensive guide

## Image Provider Management

### Quick Model Switching

The `switch_image_provider.py` utility makes it easy to change AI image models:

| Model | Cost/Image | Best For | Command |
|-------|------------|----------|---------|
| Imagen-3-Fast | $0.025 | **Recommended** | `python src/utils/switch_image_provider.py replicate imagen-3-fast` |
| SDXL | $0.0023 | Budget | `python src/utils/switch_image_provider.py replicate sdxl` |
| DALL-E 3 | $0.040 | OpenAI | `python src/utils/switch_image_provider.py openai dall-e-3` |
| Flux Dev | $0.025 | Balanced | `python src/utils/switch_image_provider.py replicate flux-dev` |

**After switching:** Restart backend with `python src/main.py`

### Cost Comparison

- **SDXL Lightning**: $0.002/image (fastest, cheapest)
- **SDXL**: $0.0023/image (budget)
- **Imagen-3-Fast**: $0.025/image (recommended)
- **Flux Dev**: $0.025/image (balanced)
- **Imagen-3-Generate**: $0.030/image (premium)
- **DALL-E 3**: $0.040/image (OpenAI)
- **Flux Pro**: $0.055/image (max quality)

## Notes

- All utilities should be run from the backend root directory
- Most utilities require proper environment configuration
- Use dry-run modes when available for safety
