"""Tests for topic generation utility."""
from bloggen.topic_utils import generate_concise_topic


def test_generate_concise_topic_basic():
    instructions = (
        "Generate an in-depth blog post explaining the transformative impact of edge AI and "
        "on-device machine learning for privacy, latency reduction, and energy efficiency in IoT devices."
    )
    topic = generate_concise_topic(instructions, enable_refine=False)
    assert 3 <= len(topic.split()) <= 12
    assert not topic.lower().startswith("generate ")


def test_generate_concise_topic_empty():
    topic = generate_concise_topic("", enable_refine=False)
    assert topic  # returns fallback
