#!/usr/bin/env python
import sys
import warnings
import logging
from datetime import datetime

from bloggen.crew import Bloggen

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Configure logging for better CrewAI output capture
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# This main file is intended to be a way for you to run your
# crew locally, so refrain from adding unnecessary logic into this file.
# Replace with inputs you want to test with, it will automatically
# interpolate any tasks and agents information

def run(_inputs):
    """
    Run the crew.
    """
    if (_inputs is None) or (not isinstance(_inputs, dict)):
        inputs = {
            'topic': 'Best tactics for Polar Wars in Age of Origins',
            'current_year': str(datetime.now().year)
        }
    else:
        inputs = _inputs
    
    # Create a logger for this run
    logger = logging.getLogger(__name__)
    logger.info(f"Starting blog generation for topic: {inputs.get('topic', 'Unknown')}")
    
    try:
        # Initialize the crew
        crew_instance = Bloggen().crew()
        logger.info("CrewAI crew initialized successfully")
        
        # Run the crew with inputs
        logger.info("Starting crew kickoff...")
        results = crew_instance.kickoff(inputs=inputs)
        
        # Extract the blog content
        blog_content = getattr(results, "raw", None)
        
        if blog_content:
            logger.info("Blog generation completed successfully")
            logger.info(f"Generated content length: {len(blog_content)} characters")
        else:
            logger.warning("Blog generation completed but no content was generated")
        
        return blog_content

    except Exception as e:
        logger.error(f"An error occurred while running the crew: {e}")
        raise Exception(f"An error occurred while running the crew: {e}")


def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        "topic": "AI LLMs",
        'current_year': str(datetime.now().year)
    }
    try:
        Bloggen().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        Bloggen().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the results.
    """
    inputs = {
        "topic": "AI LLMs",
        "current_year": str(datetime.now().year)
    }
    
    try:
        Bloggen().crew().test(n_iterations=int(sys.argv[1]), eval_llm=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while testing the crew: {e}")
