#!/usr/bin/env python3
"""
Simple test to understand how CrewAI Flows work
"""

from crewai.flow.flow import Flow, listen, start
from datetime import datetime

class SimpleTestFlow(Flow):
    """Simple test flow to understand the execution pattern"""
    
    def __init__(self):
        super().__init__()
        self.test_data = None
        
    @start()
    def start_method(self, inputs=None):
        """Start method that should trigger listeners"""
        print(f"[TEST] start_method called with inputs: {inputs}")
        
        topic = inputs.get('topic') if inputs else "Test Topic"
        print(f"[TEST] Processing topic: {topic}")
        
        return {
            "topic": topic,
            "status": "started",
            "data": "Initial data from start method"
        }
    
    @listen(start_method)
    def second_phase(self, data):
        """Second phase that should be triggered by start_method"""
        print(f"[TEST] second_phase called with data: {data}")
        
        return {
            "topic": data.get("topic"),
            "status": "second_phase_complete",
            "data": "Data from second phase"
        }
    
    @listen(second_phase)
    def final_phase(self, data):
        """Final phase that should be triggered by second_phase"""
        print(f"[TEST] final_phase called with data: {data}")
        
        self.test_data = f"Final result for topic: {data.get('topic')}"
        return self.test_data

if __name__ == "__main__":
    print("Testing CrewAI Flow execution...")
    
    # Create and test the simple flow
    test_flow = SimpleTestFlow()
    
    test_inputs = {
        'topic': 'Test Topic for Flow',
        'current_year': str(datetime.now().year)
    }
    
    print(f"Executing flow with kickoff method and inputs: {test_inputs}")
    result = test_flow.kickoff(inputs=test_inputs)
    
    print(f"Result from kickoff: {result}")
    print(f"Final test_data: {test_flow.test_data}")
    
    print("Test completed.")
