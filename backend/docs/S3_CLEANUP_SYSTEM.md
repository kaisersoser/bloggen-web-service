# S3 Image Cleanup System

## Overview

The S3 Image Cleanup System provides automated, asynchronous cleanup of S3 images when blogs are deleted, preventing orphaned images and reducing storage costs.

## Features

- ✅ **Asynchronous Cleanup**: Non-blocking blog deletion with background S3 cleanup
- ✅ **Retry Mechanism**: 3 retry attempts for failed S3 deletions with exponential backoff
- ✅ **Cost Tracking**: Integration with existing audit system for cost savings tracking
- ✅ **Quarterly Maintenance**: Automated orphaned image detection and cleanup utility
- ✅ **Comprehensive Validation**: Testing and validation tools for system reliability

## Components

### Core Components

1. **S3ImageStorage** (`core/s3_storage.py`)
   - Extended with cleanup methods: `delete_blog_images()`, `list_blog_images()`, `extract_image_urls_from_content()`
   - Batch deletion for efficiency
   - URL extraction from blog content

2. **S3CleanupQueue** (`core/s3_cleanup_queue.py`)
   - Asynchronous queue system with worker processes
   - Retry mechanism (3 attempts with exponential backoff)
   - Status tracking and error handling

3. **TaskManager Integration** (`core/task_manager.py`)
   - Modified `delete_task()` to trigger S3 cleanup
   - Non-blocking operation - blog deletion proceeds regardless of S3 cleanup status

4. **Audit System Integration** (`core/audit_tracker.py`)
   - `track_storage_cleanup()` method for cost tracking
   - Negative costs represent savings in the audit system

### Utilities

1. **Orphaned Image Cleanup** (`utils/cleanup_orphaned_images.py`)
   ```bash
   # Dry run (recommended first)
   python src/utils/cleanup_orphaned_images.py --dry-run
   
   # Actual cleanup
   python src/utils/cleanup_orphaned_images.py --force
   
   # Cost analysis only
   python src/utils/cleanup_orphaned_images.py --cost-analysis
   ```

2. **Validation & Testing** (`utils/validate_s3_cleanup.py`)
   ```bash
   # Full validation suite
   python src/utils/validate_s3_cleanup.py --full-test
   
   # Cost analysis report
   python src/utils/validate_s3_cleanup.py --cost-analysis
   
   # Test specific components
   python src/utils/validate_s3_cleanup.py --test-cleanup
   python src/utils/validate_s3_cleanup.py --audit-test
   ```

## Configuration

The system uses existing environment variables:

```env
# AWS S3 Configuration (already configured)
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_S3_BUCKET_NAME=blog-hero-images-bloggen-app
AWS_S3_REGION=eu-west-3
```

## Operation

### Automatic Cleanup (Blog Deletion)

When a blog is deleted via the API (`DELETE /tasks/{task_id}`):

1. **Database Query**: Fetch blog content and hero image URL
2. **Enqueue Cleanup**: Add cleanup task to asynchronous queue
3. **Database Deletion**: Proceed with blog deletion (non-blocking)
4. **Background Processing**: S3 cleanup happens asynchronously
5. **Retry Logic**: Up to 3 attempts with exponential backoff
6. **Audit Tracking**: Log cost savings and cleanup metrics

### Quarterly Maintenance

Schedule the orphaned image cleanup to run every 3 months:

```bash
# Crontab example (quarterly on 1st day of Jan, Apr, Jul, Oct)
0 2 1 1,4,7,10 * cd /path/to/backend && python src/utils/cleanup_orphaned_images.py --force
```

## Cost Analysis

### Current Cost Structure
- **Average image size**: ~200KB
- **S3 Standard pricing**: ~$0.023/GB/month
- **Cost per image**: ~$0.0000046/month
- **1000 images**: ~$0.0046/month (~$0.055/year)

### Projected Savings
Based on quarterly cleanup frequency:
- **Retention period**: 3 months average
- **Cost reduction**: ~75% vs. no cleanup
- **Annual savings**: Scales with image volume

## Monitoring

### Queue Status

Check cleanup queue status via the API or logs:

```python
from core.s3_cleanup_queue import get_cleanup_queue

cleanup_queue = await get_cleanup_queue()
stats = cleanup_queue.get_queue_stats()
print(stats)
```

### Audit Reports

S3 cleanup metrics are tracked in the existing audit system:
- Storage cleanup events logged as special audit sessions
- Cost savings tracked as negative costs
- Detailed metrics in application logs

## Troubleshooting

### Common Issues

1. **S3 Permission Errors**
   - Verify AWS credentials and bucket permissions
   - Run: `python src/utils/validate_s3_cleanup.py --full-test`

2. **Queue Not Processing**
   - Check application logs for worker errors
   - Verify queue is initialized in startup logs
   - Test with validation utility

3. **Orphaned Images Not Detected**
   - Run orphaned cleanup with `--dry-run` first
   - Check database connectivity
   - Verify S3 list permissions

### Validation Commands

```bash
# Test complete system
python src/utils/validate_s3_cleanup.py --full-test

# Check cost calculations
python src/utils/validate_s3_cleanup.py --cost-analysis

# Test individual components
python src/utils/validate_s3_cleanup.py --test-cleanup
```

## Implementation Details

### Safety Measures

- **Non-blocking deletion**: Blog deletion never fails due to S3 issues
- **Retry mechanism**: 3 attempts with exponential backoff
- **Dry-run mode**: All utilities support safe testing
- **Comprehensive logging**: Full audit trail for debugging
- **Graceful degradation**: System continues if S3 is unavailable

### Performance Optimizations

- **Batch operations**: S3 batch delete (up to 1000 objects)
- **Asynchronous processing**: Background workers with queue
- **Efficient pattern matching**: Minimize S3 list operations
- **Connection pooling**: Reuse S3 connections

## Next.js Configuration

Ensure S3 hostname is allowed in `next.config.ts`:

```typescript
images: {
  remotePatterns: [
    {
      protocol: 'https',
      hostname: 'blog-hero-images-bloggen-app.s3.eu-west-3.amazonaws.com',
      port: '',
      pathname: '/**',
    },
    // ... other patterns
  ],
}
```

## Maintenance Schedule

- **Immediate**: Automatic cleanup on blog deletion
- **Quarterly**: Run orphaned image cleanup utility
- **Monthly**: Review cost analysis and cleanup metrics
- **Annually**: Review cleanup frequency and cost projections

---

This system ensures efficient S3 storage management with comprehensive cost tracking and reliable cleanup mechanisms.
