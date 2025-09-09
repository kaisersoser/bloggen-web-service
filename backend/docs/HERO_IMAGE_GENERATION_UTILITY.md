# Hero Image Generation Utility

## Overview

The `generate_hero_images.py` utility is a powerful script designed to bulk generate and update hero images for existing blogs in the database. This tool is particularly useful for:

- **Retroactive Updates**: Adding hero images to blogs created before the feature was implemented
- **Batch Processing**: Generating images for multiple blogs efficiently
- **Data Migration**: Updating existing blogs after hero image system changes
- **Quality Improvements**: Regenerating images with updated prompts or AI models

## Location

```
backend/src/utils/generate_hero_images.py
```

## Features

### ✅ Smart Processing
- **Selective Updates**: Only processes blogs without existing hero images (unless forced)
- **Database Integration**: Direct connection to PostgreSQL with optimized settings
- **Error Handling**: Comprehensive error catching and logging
- **Progress Tracking**: Real-time progress updates with detailed logging

### ✅ Flexible Execution Modes
- **Dry Run Mode**: Preview what would be processed without making changes
- **Live Mode**: Actually generate and save images to database
- **Force Regeneration**: Override existing images when needed
- **Limited Processing**: Process only a specific number of blogs for testing

### ✅ AI Integration
- **OpenAI DALL-E 3**: Uses the same image generation system as the main application
- **Unsplash Fallback**: Automatic fallback to Unsplash if OpenAI fails
- **Markdown Processing**: Properly extracts image URLs from AI-generated markdown responses

## Usage

### Prerequisites

1. **Virtual Environment**: Must be activated before running
   ```bash
   cd backend && source .venv/bin/activate
   ```

2. **Environment Variables**: Ensure proper configuration in `backend/.env`
   ```env
   ENABLE_AI_IMAGE_GENERATION=true
   OPENAI_API_KEY=your_openai_key
   UNSPLASH_ACCESS_KEY=your_unsplash_key
   DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
   ```

3. **Database Connection**: PostgreSQL must be accessible

### Command Line Options

```bash
cd backend/src/utils
python generate_hero_images.py [OPTIONS]
```

#### Available Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Preview mode - no database changes | `False` |
| `--force` | Regenerate images even if they exist | `False` |
| `--limit N` | Process only N blogs (useful for testing) | No limit |

### Common Usage Scenarios

#### 1. Preview What Will Be Processed (Recommended First Step)
```bash
cd backend/src/utils
python generate_hero_images.py --dry-run
```
**Output Example:**
```
🚀 Starting Hero Image Generation Utility
Mode: DRY RUN (no changes will be made)
Force regeneration: NO
AI Image Generation Enabled: True
----------------------------------------------------------------------
🎯 Normal mode: Processing only blogs without hero images
📊 Found 33 blogs to process
----------------------------------------------------------------------
[DRY RUN] Would process blog: "NotebookLM and Comparable Applications"
[DRY RUN] Would process blog: "Current Trends in Popular Programming Languages"
...
```

#### 2. Generate Images for All Blogs Without Heroes
```bash
cd backend/src/utils
python generate_hero_images.py
```

#### 3. Test with Limited Number of Blogs
```bash
cd backend/src/utils
python generate_hero_images.py --limit 5
```

#### 4. Force Regeneration of All Images
```bash
cd backend/src/utils
python generate_hero_images.py --force
```

#### 5. Dry Run with Force (Preview Regeneration)
```bash
cd backend/src/utils
python generate_hero_images.py --dry-run --force
```

## Output and Logging

### Real-Time Progress Display
```
📝 Processing blog 15/33
  ID: cmesdlgk30001z9u2myob6kqg
  Topic: Types of Nuclear Reactors in Use Today
  Created: 2025-08-26 10:00:51.501000
  Existing hero URL: None
  🎨 Generating hero image for topic: 'Types of Nuclear Reactors in Use Today'
  ✅ OpenAI generated image: https://oaidalleapiprodscus.blob.core.windows.net/private/org-16qnB7P...
  ✅ Updated database with hero URL: https://oaidalleapiprodscus.blob.core.windows.net/private/org-16qnB7P...
  🎉 SUCCESS: Generated and saved hero image
```

### Summary Report
```
======================================================================
📊 HERO IMAGE GENERATION SUMMARY
======================================================================
Total blogs processed: 33
✅ Successfully generated: 33
💥 Errors: 0
⏭️  Skipped (already had images): 0
Mode: LIVE - Changes saved to database
======================================================================
```

## Technical Implementation

### Database Connection
- **Optimized Settings**: Uses `statement_cache_size=0` to prevent conflicts with main application
- **Connection Management**: Proper connection opening/closing for each operation
- **Error Handling**: Graceful handling of database connection issues

### Image Generation Process
1. **Topic Extraction**: Uses blog topic for image generation prompt
2. **OpenAI Integration**: Calls DALL-E 3 via OpenAI Image Tool
3. **URL Extraction**: Parses markdown response to extract actual image URL using regex
4. **Database Update**: Updates `hero_image_url` field in blogs table
5. **Validation**: Confirms successful database write

### Code Architecture
```python
# Key components:
- setup_database_connection(): Establishes PostgreSQL connection
- get_blogs_to_process(): Queries blogs based on criteria
- generate_hero_image(): Handles OpenAI image generation
- update_hero_image_in_db(): Saves URL to database
- Main processing loop with comprehensive error handling
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Errors
**Error**: `ConnectionRefusedError: Connect call failed`
**Solution**: 
- Ensure PostgreSQL is running: `sudo systemctl start postgresql`
- Verify connection string in environment variables
- Check database credentials and permissions

#### 2. OpenAI API Errors
**Error**: `OpenAI API rate limit` or `Authentication failed`
**Solution**:
- Verify `OPENAI_API_KEY` in environment variables
- Check OpenAI account billing and rate limits
- Wait and retry if rate limited

#### 3. Import Errors
**Error**: `ModuleNotFoundError` for local modules
**Solution**:
- Run from `backend/src/utils/` directory
- Ensure virtual environment is activated
- Verify all dependencies are installed

#### 4. Image Generation Disabled
**Error**: Script exits with "AI image generation is disabled"
**Solution**:
```bash
# Enable image generation
python toggle_image_generation.py enable
```

### Environment Variable Issues
```bash
# Check current configuration
grep -E "ENABLE_.*IMAGE" ../../../.env

# Expected output:
ENABLE_AI_IMAGE_GENERATION=true
ENABLE_HERO_IMAGE_GENERATION=true
ENABLE_CONTENT_IMAGE_INJECTION=true
```

## Cost Considerations

### OpenAI DALL-E 3 Pricing
- **Cost per image**: ~$0.040 USD
- **Typical run**: 30-50 blogs = $1.20-2.00 USD
- **Large batch**: 100+ blogs = $4.00+ USD

### Cost Management Tips
1. **Use dry run first** to estimate costs
2. **Use --limit** for testing before full runs
3. **Monitor OpenAI usage** in your dashboard
4. **Consider Unsplash fallback** for cost savings

## Integration with Main Application

### Shared Components
- **OpenAI Image Tool**: Same tool used in main blog generation flow
- **Environment Configuration**: Uses same config system as main app
- **Database Schema**: Updates same `hero_image_url` field
- **Error Handling**: Consistent error handling patterns

### Safety Features
- **No Conflicts**: Uses separate database connection settings
- **Idempotent**: Safe to run multiple times (won't duplicate work)
- **Validation**: Verifies successful operations before proceeding

## Best Practices

### Before Running
1. **Always start with dry run** to preview changes
2. **Test with small limit** before full batch processing
3. **Verify environment configuration** and API keys
4. **Check database connectivity** and permissions

### During Operation
1. **Monitor progress logs** for any errors
2. **Watch for rate limiting** from OpenAI API
3. **Verify database updates** are successful
4. **Stop if consistent errors occur**

### After Completion
1. **Review summary report** for success rate
2. **Test frontend display** to confirm images load
3. **Verify database integrity** with spot checks
4. **Document any issues** for future reference

## Future Enhancements

### Potential Improvements
- **Batch API calls**: Group multiple image generations
- **Resume capability**: Continue from last processed blog
- **Image quality options**: Different resolution/style settings
- **Async processing**: Parallel image generation
- **Progress persistence**: Save progress to file for large batches

### Configuration Extensions
- **Custom prompts**: Override default image generation prompts
- **Quality settings**: Adjust image resolution and style
- **Retry logic**: Configurable retry attempts for failures
- **Output formats**: Different image formats and sizes

## Related Documentation

- [`COST_TRACKING.md`](./COST_TRACKING.md) - OpenAI API cost monitoring
- [`IMAGE_INTEGRATION_ENHANCEMENT.md`](../docs/IMAGE_INTEGRATION_ENHANCEMENT.md) - Image system architecture
- [`toggle_image_generation.py`](../src/utils/toggle_image_generation.py) - Image generation toggle utility

## Support

For issues or questions regarding the hero image generation utility:

1. **Check logs** for specific error messages
2. **Review environment configuration** and API keys
3. **Test with dry run mode** to isolate issues
4. **Verify database connectivity** independently
5. **Consult related documentation** for context

The utility is designed to be robust and user-friendly, with comprehensive logging to help diagnose any issues that may arise.
