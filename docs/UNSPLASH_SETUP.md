# Unsplash Integration Setup Guide

## Overview

The blog generator includes an **intelligent image integration system** that automatically finds and inserts highly relevant, professional images into your generated blog posts. The enhanced system uses advanced relevance scoring to ensure images directly relate to your content, automatically falling back to AI generation when real photos aren't contextually appropriate.

**Key Features:**
- 🎯 **Smart relevance filtering**: Only uses images that score ≥ 0.3 on contextual relevance
- 🤖 **Automatic AI fallback**: Generates custom illustrations for abstract concepts
- 🏞️ **Intelligent source selection**: Uses real photos for practical topics, AI for technical diagrams
- 📊 **Advanced query enhancement**: Transforms generic terms into specific, visual search queries

## Setup Instructions

### 1. Get Unsplash API Credentials

1. Visit [Unsplash Developers](https://unsplash.com/developers)
2. Create a free account or sign in
3. Create a new application
4. Copy your **Access Key** (you don't need the Secret Key for this integration)

### 2. Configure Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```bash
# Unsplash API Configuration
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here

# Optional: Secret key for advanced features (not currently used)
UNSPLASH_SECRET_KEY=your_unsplash_secret_key_here
```

### 3. Test the Integration

Run the test script to verify everything works:

```bash
python test_unsplash.py
```

## How It Works

### Automatic Image Integration

When generating blog content, the AI agent will:

1. **Analyze content context** - Understand the topic and key themes
2. **Search for relevant images** - Use the Unsplash API to find professional photos
3. **Strategic placement** - Insert 2-3 images at optimal locations in the blog
4. **Proper attribution** - Include photographer credits and links as required by Unsplash

### Image Selection Process

The tool automatically:
- Extracts relevant keywords from your blog topic
- Searches Unsplash's curated collection
- Filters for high-quality, content-appropriate images
- Generates proper Markdown with alt text and attribution

### Example Output

The generated blog will include images like:

```markdown
![Artificial Intelligence and Machine Learning](https://images.unsplash.com/photo-1677442136019-21780ecad995?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w1MDcxMzJ8MHwxfHNlYXJjaHwxfHxhcnRpZmljaWFsJTIwaW50ZWxsaWdlbmNlfGVufDB8fHx8MTY0MTc2MjY2Ng&ixlib=rb-4.0.3&q=80&w=1080 "AI and Machine Learning Technology")

*Photo by [John Doe](https://unsplash.com/@johndoe) on [Unsplash](https://unsplash.com/photos/abc123)*
```

## Fallback Behavior

If the Unsplash API is unavailable or no API key is provided:

- The tool gracefully falls back to Unsplash Source API (no auth required)
- Generates placeholder images with relevant search terms
- Maintains the same Markdown format for consistency

## Features

### Intelligent Search
- **Enhanced query processing**: Automatically filters blog-specific terms and adds visual context modifiers
- **Advanced relevance scoring**: Only accepts images with relevance score ≥ 0.3 based on metadata analysis
- **Semantic keyword grouping**: Context-aware scoring using domain-specific keyword groups (AI/ML, business, security, etc.)
- **Technical term preservation**: Keeps important technical acronyms and specialized terminology

### Professional Quality with Intelligence
- **Relevance-first approach**: Quality over quantity - rejects irrelevant images automatically
- **Smart source selection**: Uses Unsplash for real-world photos, AI generation for abstract concepts
- **Automatic fallback**: Seamlessly switches to AI generation when Unsplash images aren't relevant enough
- **Consistent output**: Always returns contextually appropriate, professional-grade images

### Advanced Fallback System
- **Intelligent relevance detection**: Automatically identifies when Unsplash results don't match content context
- **Seamless AI integration**: Falls back to OpenAI DALL-E for custom illustrations when needed
- **Context-aware prompts**: Generates different AI prompts for hero images vs supporting visuals
- **No manual intervention**: Agents get optimal images without complex decision logic

### SEO Optimized
- Generates descriptive alt text for accessibility
- Includes proper image captions
- Maintains photographer attribution for credibility

### Responsive Design
- Images automatically scale for mobile devices
- Optimized for fast loading and good UX
- Professional styling with borders and shadows

## Usage in Blog Generation

Simply generate a blog as usual - the image integration is automatic! The AI agent will:

1. Research your topic thoroughly
2. Create engaging content with **automatic image integration**
3. Fact-check and verify information
4. Polish and finalize with properly formatted images

## Troubleshooting

### No Images Appearing
- Check your `UNSPLASH_ACCESS_KEY` in `.env`
- Run `python test_unsplash.py` to verify setup
- Check the console logs for any API errors

### Poor Image Quality
- The tool automatically selects high-quality images
- If results are poor, try more specific blog topics
- Consider adding more descriptive keywords to your topic

### API Rate Limits
- Free Unsplash accounts have 50 requests/hour
- For higher volume, consider upgrading your Unsplash plan
- The tool includes automatic fallbacks for rate limit scenarios

## Cost and Limits

- **Free Tier**: 50 requests/hour (plenty for most blog generation)
- **No additional costs** - Unsplash images are free to use with attribution
- **Automatic attribution** - The tool handles all licensing requirements

## Advanced Configuration

You can customize the image integration by modifying the tool parameters in the code:

```python
# In flows.py, you can adjust:
- Image count (1-3 per blog)
- Orientation preferences (landscape, portrait, squarish)  
- Search query enhancement
- Image placement strategy
```

For questions or issues, check the console logs or run the test script for diagnostics.
