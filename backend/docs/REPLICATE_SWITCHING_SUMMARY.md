# Replicate Integration - Easy Model Switching

## What Was Done

### 1. **Comprehensive Documentation** 📚
- Created `backend/docs/IMAGE_PROVIDER_GUIDE.md` (600+ lines)
- Complete guide to all available models and costs
- Step-by-step switching instructions
- Troubleshooting section

### 2. **Easy Switching Script** 🔄
- Created `backend/src/utils/switch_image_provider.py`
- One-command model switching
- Built-in model catalog with 7 providers
- Automatic validation and error handling

### 3. **Enhanced Configuration** ⚙️
- Updated `.env.local` with inline switching examples
- Added helpful comments for quick reference
- Documented all available models with costs

### 4. **Improved Code** 💻
- Updated `ReplicateImageTool` to accept configurable model and cost
- Enhanced `tools_manager.py` to log provider/model/cost on startup
- Better cost tracking with configured per-image pricing
- More descriptive logging messages

## How to Switch Models (3 Ways)

### Method 1: Quick Switch Script (Recommended)
```bash
cd backend
source .venv/bin/activate

# List all available models
python src/utils/switch_image_provider.py --list

# Switch to a different model
python src/utils/switch_image_provider.py replicate imagen-3-fast  # Current default
python src/utils/switch_image_provider.py replicate sdxl           # Budget option
python src/utils/switch_image_provider.py openai dall-e-3          # OpenAI

# Restart backend
python src/main.py
```

### Method 2: Manual Edit .env.local
```bash
# Edit backend/.env.local and change these 3 lines:
IMAGE_PROVIDER=replicate
IMAGE_MODEL=google/imagen-3-fast
IMAGE_COST_PER_GENERATION=0.025

# Restart backend
cd backend && source .venv/bin/activate && python src/main.py
```

### Method 3: Environment Variables
```bash
# Temporary override for testing
cd backend
source .venv/bin/activate
IMAGE_PROVIDER=replicate IMAGE_MODEL=stability-ai/sdxl IMAGE_COST_PER_GENERATION=0.0023 python src/main.py
```

## Available Models Quick Reference

| Model Alias | Provider | Cost/Image | Best For |
|-------------|----------|------------|----------|
| `imagen-3-fast` | Replicate | $0.025 | **Recommended default** |
| `imagen-3-generate` | Replicate | $0.030 | Premium quality |
| `sdxl` | Replicate | $0.0023 | **Budget (94% cheaper!)** |
| `sdxl-lightning` | Replicate | $0.0020 | Maximum speed |
| `flux-dev` | Replicate | $0.025 | Balanced quality |
| `flux-pro` | Replicate | $0.055 | Maximum quality |
| `dall-e-3` | OpenAI | $0.040 | Creative compositions |

## What Makes Switching Easy

### 1. **Single Source of Truth**
All configuration in `.env.local`:
- `IMAGE_PROVIDER` - Which service (replicate/openai)
- `IMAGE_MODEL` - Which specific model
- `IMAGE_COST_PER_GENERATION` - Cost tracking

### 2. **Automatic Cost Tracking**
Cost is passed to `ReplicateImageTool` constructor and tracked automatically:
```python
tools.append(ReplicateImageTool(
    api_key=config.api.replicate_key,
    model=image_model,              # From IMAGE_MODEL env var
    cost_per_image=image_cost,      # From IMAGE_COST_PER_GENERATION env var
    audit_tracker=self.audit_tracker
))
```

### 3. **Clear Logging**
Backend startup shows exactly what's configured:
```
🎨 Loading image provider: replicate (model: google/imagen-3-fast, cost: $0.025/image)
✅ UnsplashImageTool + ReplicateImageTool loaded (google/imagen-3-fast)
```

### 4. **Validation Built-In**
Script validates:
- Model exists in catalog
- Provider matches model
- API key is present (warning if missing)
- .env.local file exists

### 5. **Comprehensive Documentation**
Three levels of docs:
1. **Quick reference** - Inline comments in `.env.local`
2. **Tool help** - `python switch_image_provider.py --help`
3. **Full guide** - `docs/IMAGE_PROVIDER_GUIDE.md`

## Example: Switching for Cost Testing

Let's say you want to test the ultra-budget SDXL model:

```bash
# Switch to SDXL (96% cheaper than your current model!)
cd backend && source .venv/bin/activate
python src/utils/switch_image_provider.py replicate sdxl

# Output:
# ✅ Updated .env.local
#    Provider: replicate
#    Model: stability-ai/sdxl
#    Cost: $0.0023/image
#
# 🔄 Next steps:
# 1. Restart the backend...

# Restart backend
python src/main.py

# You'll see in logs:
# 🎨 Loading image provider: replicate (model: stability-ai/sdxl, cost: $0.0023/image)
# 💰 Tracked stability-ai/sdxl image cost: $0.0023
```

## Example: Adding a New Provider in the Future

Adding support for a hypothetical "MidjourneyAPI" would require:

1. **Create tool class** (30 lines):
   - `backend/src/bloggen/tools/midjourney_image_tool.py`
   - Inherit from `BaseTool`, implement `_run()`

2. **Update tools manager** (3 lines):
   - Add `elif provider == 'midjourney':` case
   - Import and instantiate `MidjourneyImageTool`

3. **Update config** (2 lines):
   - Add `midjourney_key` to `APIConfig`

4. **Update switch script** (1 line):
   - Add model to `MODELS` dictionary

5. **Test**:
   - `python switch_image_provider.py midjourney model-name`

That's it! The architecture is designed for easy extension.

## Testing Checklist

Before committing, verify:
- [ ] Switch script lists all 7 models
- [ ] Manual .env.local edit works
- [ ] Backend logs show correct provider/model/cost
- [ ] Image generation works end-to-end
- [ ] Cost tracking shows correct amount
- [ ] Documentation is accurate

## Files Changed

### Created:
1. `backend/docs/IMAGE_PROVIDER_GUIDE.md` - Comprehensive guide (600+ lines)
2. `backend/src/utils/switch_image_provider.py` - Switching utility (150+ lines)
3. `backend/docs/REPLICATE_SWITCHING_SUMMARY.md` - This file

### Modified:
1. `backend/.env.local` - Added switching examples and comments
2. `backend/src/bloggen/tools/replicate_image_tool.py` - Configurable model/cost
3. `backend/src/bloggen/tools_manager.py` - Enhanced logging and parameter passing
4. `backend/src/core/config.py` - Already done (Replicate config fields)

## Cost Comparison Summary

| Scenario | Current (Imagen-3-Fast) | If Using SDXL | Savings |
|----------|------------------------|---------------|---------|
| Per image | $0.025 | $0.0023 | **91% cheaper** |
| Per blog (3 images) | $0.075 | $0.0069 | **91% cheaper** |
| 100 blogs | $7.50 | $0.69 | **Save $6.81** |
| 1000 blogs | $75.00 | $6.90 | **Save $68.10** |

vs Original DALL-E 3:
| Scenario | DALL-E 3 | Imagen-3-Fast | Savings |
|----------|----------|---------------|---------|
| Per image | $0.040 | $0.025 | **37.5% cheaper** |
| 100 blogs | $12.00 | $7.50 | **Save $4.50** |

## Next Steps

1. ✅ Code is ready and documented
2. ⏳ Test end-to-end with current Imagen-3-Fast config
3. ⏳ Optionally test switching to SDXL to see quality difference
4. ⏳ Commit changes to Git
5. ⏳ Deploy to production

---

**Bottom Line:** Switching image providers is now as simple as:
```bash
python src/utils/switch_image_provider.py <provider> <model-alias>
```

The entire system (configuration, tool loading, cost tracking, logging) updates automatically! 🎉
