#!/bin/bash
# Simple script to run the HTTPS test in an isolated way
cd /home/vogtcha/Jupyter/Projects/CrewAI/bloggen-web-service
source backend/.venv/bin/activate
python test_https_blog_generation.py
