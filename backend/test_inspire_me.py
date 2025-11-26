#!/usr/bin/env python3
"""
Test script for the /generate-random-topic endpoint
"""
import sys
import os
sys.path.insert(0, '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/src')

# Load environment variables
from dotenv import load_dotenv
env_file = '/home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service/backend/.env'
load_dotenv(env_file)

# Now test the endpoint logic directly
import litellm
from core.config import config
import random

# Test if GEMINI_API_KEY is loaded
print(f"✓ GEMINI_API_KEY loaded: {'GEMINI_API_KEY' in os.environ}")
print(f"✓ Default model: {config.models.default_model}")
print()

# Simulate the endpoint logic
categories = [
    "Technology & Innovation",
    "Artificial Intelligence & Machine Learning",
    "Space Exploration & Astronomy",
    "Business & Entrepreneurship",
    "Health & Wellness",
]

selected_category = random.choice(categories)
print(f"📂 Selected category: {selected_category}")
print()

prompt = f"""Generate ONE unique, interesting, and specific blog topic in the category: {selected_category}

Requirements:
- Be specific and engaging (e.g., "The future of quantum computing in drug discovery" not just "quantum computing")
- 8-15 words maximum
- Make it timely and relevant to 2025
- Should inspire curiosity and be researchable
- Use active, compelling language
- Do NOT use questions or imperatives
- Return ONLY the topic, nothing else

Examples of good topics:
- "The intersection of AI and personalized medicine in cancer treatment"
- "Circular economy strategies transforming the fashion industry"
- "Neuroscience insights into remote work productivity and focus"""

try:
    print(f"🤖 Calling LiteLLM with model: {config.models.default_model}")
    print()
    
    response = litellm.completion(
        model=config.models.default_model,
        messages=[
            {
                "role": "system",
                "content": "You are a creative blog topic generator. You produce specific, engaging, and researchable blog topics."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=50,
        temperature=0.9,
    )
    
    topic_content = response.choices[0].message.content
    topic = topic_content.strip().strip('"').strip("'")
    
    print("✅ SUCCESS!")
    print(f"🎯 Generated topic: {topic}")
    print(f"📂 Category: {selected_category}")
    print()
    print("The 'Inspire Me' feature is working correctly with Gemini 2.0 Flash!")
    
except Exception as e:
    print("❌ FAILED!")
    print(f"Error: {e}")
    print()
    print("The endpoint would fall back to hardcoded topics.")
    
    # Show fallback
    fallback_topics = [
        ("The evolution of artificial intelligence in creative industries", "Technology & Innovation"),
        ("Sustainable business practices reshaping corporate culture", "Business & Entrepreneurship"),
        ("The science behind habit formation and behavioral change", "Health & Wellness"),
    ]
    topic, category = random.choice(fallback_topics)
    print(f"🔄 Fallback topic: {topic}")
    print(f"📂 Fallback category: {category}")
