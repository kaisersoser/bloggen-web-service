# Image Provider Configuration Guide

## Overview

The blog generation service supports multiple AI image generation providers with easy switching between them. This guide explains how to configure and switch between different providers and models.

## Supported Providers

### 1. **Replicate** (Current Default)
- **Provider**: `replicate`
- **Best For**: Cost-effective, high-quality images
- **Cost**: $0.025/image (Google Imagen-3-Fast)
- **Quality**: Photorealistic, professional-grade images
- **Speed**: Fast generation (~2-4 seconds)

### 2. **OpenAI DALL-E 3**
- **Provider**: `openai`
- **Best For**: Consistent style, creative compositions
- **Cost**: $0.040/image
- **Quality**: Excellent creative interpretations
- **Speed**: Moderate (~5-10 seconds)

### 3. **Unsplash** (Free Fallback)
- **Always Active**: Automatically used as fallback
- **Cost**: Free (stock photos)
- **Quality**: Professional stock photography
- **Limitation**: May not be specific to content

## Quick Provider Switch

### Switch to Replicate (Google Imagen-3-Fast)

```bash
# Edit backend/.env.local
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-fast
IMAGE_COST_PER_GENERATION=0.025
REPLICATE_API_KEY=your_replicate_api_key_here
```

### Switch to OpenAI DALL-E 3

```bash
# Edit backend/.env.local
IMAGE_PROVIDER=openai
IMAGE_MODEL=dall-e-3
IMAGE_COST_PER_GENERATION=0.040
OPENAI_API_KEY=your_openai_api_key_here
```

**After changing configuration:**
```bash
cd backend
source .venv/bin/activate
python src/main.py  # Restart backend to load new config
```

## Available Replicate Models

### Google Imagen Models

#### Imagen-3-Fast (Recommended)
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-fast
IMAGE_COST_PER_GENERATION=0.025
```
- **Best for**: Fast, cost-effective, high-quality
- **Speed**: ~2-4 seconds
- **Cost**: $0.025/image

#### Imagen-3-Generate
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-generate
IMAGE_COST_PER_GENERATION=0.030
```
- **Best for**: Higher quality, more refined details
- **Speed**: ~4-6 seconds
- **Cost**: $0.030/image

### Stable Diffusion Models

#### SDXL (Ultra Low Cost)
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=stability-ai/sdxl
IMAGE_COST_PER_GENERATION=0.0023
```
- **Best for**: Budget-conscious projects
- **Speed**: ~3-5 seconds
- **Cost**: $0.0023/image (94% cheaper than DALL-E 3!)

#### SDXL Lightning (Fastest)
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=bytedance/sdxl-lightning-4step
IMAGE_COST_PER_GENERATION=0.0020
```
- **Best for**: Maximum speed, minimal cost
- **Speed**: ~1-2 seconds
- **Cost**: $0.0020/image

### Flux Models (Premium Quality)

#### Flux Pro
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=black-forest-labs/flux-pro
IMAGE_COST_PER_GENERATION=0.055
```
- **Best for**: Maximum quality, creative projects
- **Speed**: ~10-15 seconds
- **Cost**: $0.055/image

#### Flux Dev
```bash
IMAGE_PROVIDER=replicate
IMAGE_MODEL=black-forest-labs/flux-dev
IMAGE_COST_PER_GENERATION=0.025
```
- **Best for**: Good balance of quality and cost
- **Speed**: ~5-8 seconds
- **Cost**: $0.025/image

## Configuration File Reference

### Environment Variables (.env.local)

```bash
# =============================================================================
# IMAGE GENERATION CONFIGURATION
# =============================================================================

# Master toggles (enable/disable AI image generation)
ENABLE_AI_IMAGE_GENERATION=true          # Master switch
ENABLE_HERO_IMAGE_GENERATION=true        # Hero images in blog
ENABLE_CONTENT_IMAGE_INJECTION=true      # Images within content

# Provider Selection
IMAGE_PROVIDER=replicate                  # Options: replicate | openai
IMAGE_MODEL=google/imagen-3-fast          # Model identifier (provider-specific)
IMAGE_COST_PER_GENERATION=0.025          # Cost per image in USD

# API Keys
REPLICATE_API_KEY=your_key_here          # Required if IMAGE_PROVIDER=replicate
OPENAI_API_KEY=your_key_here             # Required if IMAGE_PROVIDER=openai
UNSPLASH_ACCESS_KEY=your_key_here        # Always required (free fallback)
```

## Cost Comparison Table

| Provider | Model | Cost/Image | Quality | Speed | Best For |
|----------|-------|------------|---------|-------|----------|
| Replicate | Imagen-3-Fast | $0.025 | ⭐⭐⭐⭐ | Fast | **Recommended default** |
| Replicate | Imagen-3-Generate | $0.030 | ⭐⭐⭐⭐⭐ | Medium | Premium quality |
| Replicate | SDXL | $0.0023 | ⭐⭐⭐ | Medium | Budget projects |
| Replicate | SDXL Lightning | $0.0020 | ⭐⭐⭐ | Very Fast | Maximum speed |
| Replicate | Flux Pro | $0.055 | ⭐⭐⭐⭐⭐ | Slow | Creative/artistic |
| Replicate | Flux Dev | $0.025 | ⭐⭐⭐⭐ | Medium | Balanced choice |
| OpenAI | DALL-E 3 | $0.040 | ⭐⭐⭐⭐ | Medium | Creative compositions |
| Unsplash | Stock Photos | Free | ⭐⭐⭐ | Instant | Fallback |

## Adding New Providers

### Step 1: Create Tool Class

Create a new file in `backend/src/bloggen/tools/`:

```python
# Example: backend/src/bloggen/tools/stability_image_tool.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, Type

class StabilityImageInput(BaseModel):
    prompt: str = Field(..., description="Image description")
    size: str = Field("1024x1024", description="Image size")
    
class StabilityImageTool(BaseTool):
    name: str = "stability_image_generate"
    description: str = "Generate images using Stability AI"
    args_schema: Type[BaseModel] = StabilityImageInput
    
    def __init__(self, api_key: str, model: str, audit_tracker=None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._model = model
        self._audit_tracker = audit_tracker
        
    def _run(self, prompt: str, size: str = "1024x1024", **kwargs) -> str:
        # Implement your provider's API integration here
        # Return markdown image tag: ![alt](url "caption")
        pass
```

### Step 2: Update Tools Manager

Edit `backend/src/bloggen/tools_manager.py`:

```python
def _load_content_tools(self) -> list:
    tools = []
    
    # Always load free Unsplash fallback
    tools.append(UnsplashImageTool(...))
    
    # Load AI provider based on config
    provider = self.config.api.image_provider
    
    if provider == "replicate":
        from .tools.replicate_image_tool import ReplicateImageTool
        tools.append(ReplicateImageTool(...))
    elif provider == "openai":
        from .tools.openai_image_tool import OpenAIImageTool
        tools.append(OpenAIImageTool(...))
    elif provider == "stability":  # NEW PROVIDER
        from .tools.stability_image_tool import StabilityImageTool
        tools.append(StabilityImageTool(...))
    else:
        # Default to Replicate
        from .tools.replicate_image_tool import ReplicateImageTool
        tools.append(ReplicateImageTool(...))
    
    return tools
```

### Step 3: Update Configuration

Edit `backend/src/core/config.py`:

```python
@dataclass
class APIConfig:
    # Existing fields...
    stability_key: Optional[str] = None  # NEW
    
    # In _init_api() method:
    stability_key=os.getenv("STABILITY_API_KEY"),
```

### Step 4: Update Environment File

Add to `.env.local`:

```bash
IMAGE_PROVIDER=stability
IMAGE_MODEL=stable-diffusion-xl-1024-v1-0
IMAGE_COST_PER_GENERATION=0.0030
STABILITY_API_KEY=your_stability_api_key_here
```

### Step 5: Test New Provider

```bash
cd backend
source .venv/bin/activate
python src/main.py
# Generate a test blog and verify images work
```

## Troubleshooting

### Images Not Generating

1. **Check provider configuration:**
   ```bash
   grep IMAGE_PROVIDER backend/.env.local
   ```

2. **Verify API key is set:**
   ```bash
   grep REPLICATE_API_KEY backend/.env.local  # or OPENAI_API_KEY
   ```

3. **Check backend logs:**
   ```bash
   tail -f backend/logs/app.log
   ```

4. **Verify feature flags:**
   ```bash
   grep ENABLE_.*IMAGE backend/.env.local
   ```

### Wrong Provider Being Used

1. **Restart backend after config changes:**
   ```bash
   cd backend && source .venv/bin/activate && python src/main.py
   ```

2. **Check config loading in logs:**
   - Look for "Image provider: replicate" or similar
   - Look for "✅ ReplicateImageTool loaded" or "✅ OpenAIImageTool loaded"

### Cost Tracking Issues

1. **Verify IMAGE_COST_PER_GENERATION matches your model:**
   - Imagen-3-Fast: `0.025`
   - DALL-E 3: `0.040`
   - SDXL: `0.0023`

2. **Check audit logs:**
   ```python
   # In PostgreSQL
   SELECT model, cost, phase FROM api_calls WHERE phase = 'image_generation';
   ```

## Best Practices

### 1. **Development vs Production**

Use different providers for different environments:

```bash
# Development (.env.local) - Use cheaper models for testing
IMAGE_PROVIDER=replicate
IMAGE_MODEL=bytedance/sdxl-lightning-4step
IMAGE_COST_PER_GENERATION=0.0020

# Production (.env) - Use higher quality
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-fast
IMAGE_COST_PER_GENERATION=0.025
```

### 2. **Cost Optimization**

- **Budget-Conscious**: Use SDXL ($0.0023/image)
- **Balanced**: Use Imagen-3-Fast ($0.025/image)
- **Premium**: Use DALL-E 3 or Flux Pro ($0.040-0.055/image)

### 3. **Fallback Strategy**

The system automatically uses Unsplash (free) if:
- AI image generation fails
- API quota exceeded
- Provider API is down

### 4. **Monitor Costs**

```bash
# Check daily image generation costs
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://localhost:5000/api/analytics/costs?start_date=2025-10-01&end_date=2025-10-13
```

### 5. **Testing New Providers**

1. Test with IMAGE_PROVIDER=new_provider in `.env.local`
2. Generate 2-3 test blogs to verify quality
3. Check cost tracking accuracy
4. Monitor error logs for issues
5. Switch production only after successful testing

## Quick Reference Commands

```bash
# Check current provider configuration
grep -E "IMAGE_PROVIDER|IMAGE_MODEL|IMAGE_COST" backend/.env.local

# Switch to Replicate Imagen-3-Fast (recommended)
cat >> backend/.env.local << EOF
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-fast
IMAGE_COST_PER_GENERATION=0.025
EOF

# Switch to OpenAI DALL-E 3
cat >> backend/.env.local << EOF
IMAGE_PROVIDER=openai
IMAGE_MODEL=dall-e-3
IMAGE_COST_PER_GENERATION=0.040
EOF

# Disable AI image generation (use only free Unsplash)
cd backend && source .venv/bin/activate
python src/utils/toggle_image_generation.py disable

# Re-enable AI image generation
cd backend && source .venv/bin/activate
python src/utils/toggle_image_generation.py enable

# Restart backend to apply changes
cd backend && source .venv/bin/activate && python src/main.py
```

## Support

For issues or questions:
1. Check backend logs: `backend/logs/app.log`
2. Review this guide's troubleshooting section
3. Test with Unsplash-only mode first (disable AI generation)
4. Verify API keys are valid and have sufficient quota
