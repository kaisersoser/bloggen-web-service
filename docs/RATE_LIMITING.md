# Rate Limiting Configuration

This document describes the environment variables available for configuring rate limiting in the blog generation service.

## Environment Variables

### Core Rate Limiting Settings

```bash
# Enable/disable rate limiting (default: true)
RATE_LIMIT_ENABLED=true

# Token limits per minute (default: 30000 - OpenAI's standard limit)
RATE_LIMIT_TOKENS_PER_MINUTE=30000

# Request limits per minute (default: 3500 - OpenAI's standard limit)  
RATE_LIMIT_REQUESTS_PER_MINUTE=3500

# Maximum retry attempts for failed requests (default: 5)
RATE_LIMIT_MAX_RETRIES=5

# Base delay between retries in seconds (default: 1.0)
RATE_LIMIT_BASE_DELAY=1.0

# Maximum delay between retries in seconds (default: 60.0)
RATE_LIMIT_MAX_DELAY=60.0

# Enable request chunking for large requests (default: true)
RATE_LIMIT_ENABLE_CHUNKING=true
```

## Common Configurations

### For Free Tier OpenAI Users
```bash
RATE_LIMIT_TOKENS_PER_MINUTE=3000
RATE_LIMIT_REQUESTS_PER_MINUTE=200
RATE_LIMIT_MAX_RETRIES=3
```

### For High-Volume Usage
```bash
RATE_LIMIT_TOKENS_PER_MINUTE=90000
RATE_LIMIT_REQUESTS_PER_MINUTE=10000
RATE_LIMIT_BASE_DELAY=0.5
```

### To Disable Rate Limiting
```bash
RATE_LIMIT_ENABLED=false
```

## How It Works

1. **Token Bucket Algorithm**: The system uses a token bucket to track token and request usage
2. **Exponential Backoff**: Failed requests are retried with increasing delays
3. **Graceful Fallback**: If rate limiting fails, the system falls back to direct execution
4. **Phase-Aware**: Different blog generation phases can have different token estimates

## Benefits

- **Prevents Rate Limit Errors**: Avoids hitting OpenAI API limits
- **Automatic Retry**: Transient failures are handled automatically
- **Configurable**: Easily adjust limits based on your OpenAI plan
- **Safe**: Always falls back to working state if issues occur

## Testing

To test rate limiting configuration:

```bash
cd backend
source .venv/bin/activate
python3 -c "
from src.core.config import config
print(f'Rate limiting: {config.rate_limit.enabled}')
print(f'Limits: {config.rate_limit.tokens_per_minute} TPM, {config.rate_limit.requests_per_minute} RPM')
"
```

## Troubleshooting

### Still Getting Rate Limit Errors?

1. **Reduce token limits**: Lower `RATE_LIMIT_TOKENS_PER_MINUTE`
2. **Increase delays**: Higher `RATE_LIMIT_BASE_DELAY` and `RATE_LIMIT_MAX_DELAY`
3. **Check OpenAI plan**: Verify your actual API limits match the configuration

### Rate Limiting Too Aggressive?

1. **Increase limits**: Higher token and request limits
2. **Reduce delays**: Lower delay values for faster execution
3. **Disable if needed**: Set `RATE_LIMIT_ENABLED=false` temporarily
