#!/usr/bin/env python3
"""Quick script to switch image generation providers.

Usage:
    # Switch to Replicate Imagen-3-Fast (recommended default)
    python switch_image_provider.py replicate imagen-3-fast
    
    # Switch to Replicate SDXL (budget option)
    python switch_image_provider.py replicate sdxl
    
    # Switch to OpenAI DALL-E 3
    python switch_image_provider.py openai dall-e-3
    
    # See all available models
    python switch_image_provider.py --list
"""

import os
import sys
from pathlib import Path

# Model configurations: (provider, model_identifier, cost_per_image)
MODELS = {
    # Replicate models
    "imagen-3-fast": ("replicate", "google/imagen-3-fast", 0.025),
    "imagen-3-generate": ("replicate", "google/imagen-3-generate", 0.030),
    "sdxl": ("replicate", "stability-ai/sdxl", 0.0023),
    "sdxl-lightning": ("replicate", "bytedance/sdxl-lightning-4step", 0.0020),
    "flux-pro": ("replicate", "black-forest-labs/flux-pro", 0.055),
    "flux-dev": ("replicate", "black-forest-labs/flux-dev", 0.025),
    
    # OpenAI models
    "dall-e-3": ("openai", "dall-e-3", 0.040),
}

def list_models():
    """Print all available models with details."""
    print("\n🎨 Available Image Generation Models:\n")
    print(f"{'Model Alias':<20} {'Provider':<12} {'Model ID':<35} {'Cost/Image'}")
    print("-" * 85)
    
    for alias, (provider, model_id, cost) in sorted(MODELS.items()):
        print(f"{alias:<20} {provider:<12} {model_id:<35} ${cost:.4f}")
    
    print("\n💡 Usage Examples:")
    print("  python switch_image_provider.py replicate imagen-3-fast")
    print("  python switch_image_provider.py replicate sdxl")
    print("  python switch_image_provider.py openai dall-e-3")
    print()

def update_env_file(provider: str, model: str, cost: float):
    """Update .env.local with new image provider configuration."""
    # Look for .env.local in backend root directory
    backend_root = Path(__file__).parent.parent.parent
    env_file = backend_root / ".env.local"
    
    if not env_file.exists():
        print(f"❌ Error: {env_file} not found!")
        print(f"Looked in: {env_file.absolute()}")
        sys.exit(1)
    
    # Read existing content
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update configuration lines
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('IMAGE_PROVIDER='):
            lines[i] = f'IMAGE_PROVIDER={provider}\n'
            updated = True
        elif line.startswith('IMAGE_MODEL='):
            lines[i] = f'IMAGE_MODEL={model}\n'
            updated = True
        elif line.startswith('IMAGE_COST_PER_GENERATION='):
            lines[i] = f'IMAGE_COST_PER_GENERATION={cost}\n'
            updated = True
    
    if not updated:
        print("⚠️  Warning: Could not find IMAGE_PROVIDER configuration in .env.local")
        print("Please manually add these lines to your .env.local:")
        print(f"IMAGE_PROVIDER={provider}")
        print(f"IMAGE_MODEL={model}")
        print(f"IMAGE_COST_PER_GENERATION={cost}")
        sys.exit(1)
    
    # Write updated content
    with open(env_file, 'w') as f:
        f.writelines(lines)
    
    print(f"✅ Updated {env_file}")
    print(f"   Provider: {provider}")
    print(f"   Model: {model}")
    print(f"   Cost: ${cost}/image")

def main():
    if len(sys.argv) == 1 or '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    if '--list' in sys.argv or '-l' in sys.argv:
        list_models()
        sys.exit(0)
    
    if len(sys.argv) < 3:
        print("❌ Error: Not enough arguments")
        print(__doc__)
        sys.exit(1)
    
    provider_arg = sys.argv[1].lower()
    model_alias = sys.argv[2].lower()
    
    # Validate model alias
    if model_alias not in MODELS:
        print(f"❌ Error: Unknown model alias '{model_alias}'")
        print("\n📋 Available models:")
        list_models()
        sys.exit(1)
    
    provider, model, cost = MODELS[model_alias]
    
    # Validate provider matches
    if provider_arg != provider:
        print(f"⚠️  Warning: Model '{model_alias}' belongs to provider '{provider}', not '{provider_arg}'")
        print(f"Using correct provider: {provider}")
    
    # Check API key
    api_key_var = "REPLICATE_API_KEY" if provider == "replicate" else "OPENAI_API_KEY"
    if not os.getenv(api_key_var):
        print(f"⚠️  Warning: {api_key_var} not found in environment")
        print(f"Make sure to add it to .env.local before restarting the backend")
    
    # Update configuration
    update_env_file(provider, model, cost)
    
    print("\n🔄 Next steps:")
    print("1. Restart the backend to load new configuration:")
    print("   cd backend && source .venv/bin/activate && python src/main.py")
    print("2. Generate a test blog to verify the new model works")
    print("3. Check logs for image generation success messages")
    print(f"4. Verify cost tracking shows ${cost}/image")
    print()

if __name__ == '__main__':
    main()
