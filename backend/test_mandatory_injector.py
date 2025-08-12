#!/usr/bin/env python3
"""
Test the mandatory image injector to ensure every blog gets 2-3 images.
"""

import sys
import os

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from bloggen.mandatory_image_injector import create_mandatory_image_injector

def test_image_injector():
    """Test the mandatory image injector with various scenarios"""
    print("🔧 TESTING MANDATORY IMAGE INJECTOR")
    print("=" * 60)
    
    # Create the injector
    injector = create_mandatory_image_injector()
    
    # Test 1: Blog with no images
    print("\n📝 TEST 1: Blog with 0 images")
    content_no_images = """
# AI in Healthcare

This is an introduction about AI in healthcare.

## Benefits of AI

AI provides many benefits in healthcare settings.

## Implementation

Here's how to implement AI solutions.

## Conclusion

AI will transform healthcare.
"""
    
    result1 = injector.ensure_adequate_images(content_no_images, "AI in Healthcare")
    image_count1 = result1.count('![')
    print(f"   Before: 0 images")
    print(f"   After: {image_count1} images")
    print(f"   ✅ Success: {image_count1 >= 2}")
    
    # Test 2: Blog with 1 image (needs 1 more)
    print("\n📝 TEST 2: Blog with 1 image")
    content_one_image = """
# Machine Learning Basics

Introduction to machine learning concepts.

![ML Concept](https://example.com/ml.jpg "Machine Learning")

## Algorithms

Different types of machine learning algorithms.

## Applications

Real-world applications of ML.
"""
    
    result2 = injector.ensure_adequate_images(content_one_image, "Machine Learning")
    image_count2 = result2.count('![')
    print(f"   Before: 1 image")
    print(f"   After: {image_count2} images")
    print(f"   ✅ Success: {image_count2 >= 2}")
    
    # Test 3: Blog with adequate images (should not change)
    print("\n📝 TEST 3: Blog with 2 images (adequate)")
    content_adequate = """
# Data Science Guide

Introduction to data science.

![Data Science](https://example.com/ds1.jpg "Data Science")

## Tools

Popular data science tools.

![Tools](https://example.com/ds2.jpg "Tools")

## Conclusion

Summary of data science.
"""
    
    result3 = injector.ensure_adequate_images(content_adequate, "Data Science")
    image_count3 = result3.count('![')
    print(f"   Before: 2 images")
    print(f"   After: {image_count3} images")
    print(f"   ✅ Success: {image_count3 == 2} (unchanged)")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Test 1 (0→{image_count1}): {'✅ PASS' if image_count1 >= 2 else '❌ FAIL'}")
    print(f"   Test 2 (1→{image_count2}): {'✅ PASS' if image_count2 >= 2 else '❌ FAIL'}")
    print(f"   Test 3 (2→{image_count3}): {'✅ PASS' if image_count3 == 2 else '❌ FAIL'}")
    
    # Show a sample of the enhanced content
    print(f"\n🔍 SAMPLE ENHANCED CONTENT (Test 1):")
    print("=" * 40)
    lines = result1.split('\n')
    for i, line in enumerate(lines[:15], 1):
        print(f"{i:2d}: {line}")
    if len(lines) > 15:
        print("    ... (truncated)")

if __name__ == "__main__":
    test_image_injector()
