"""
Cost Calculator for LLM API Calls

Handles cost calculation logic for different AI models.
Follows Single Responsibility Principle - only calculates costs.
"""

from typing import Dict
from bloggen.constants import OPENAI_PRICING, normalize_model_name


class CostCalculator:
    """Calculates costs for different LLM models based on token usage."""
    
    @classmethod
    def calculate_cost(cls, model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
        """Calculate costs for a model's token usage."""
        # Use centralized pricing from constants
        normalized_model = normalize_model_name(model)
        pricing = OPENAI_PRICING.get(normalized_model, OPENAI_PRICING['gpt-4o-mini'])
        
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        total_cost = input_cost + output_cost
        
        return {
            'input_cost': input_cost,
            'output_cost': output_cost,
            'total_cost': total_cost
        }
    
    @classmethod
    def get_model_pricing(cls, model: str) -> Dict[str, float]:
        """Get pricing information for a specific model."""
        normalized_model = normalize_model_name(model)
        return OPENAI_PRICING.get(normalized_model, OPENAI_PRICING['gpt-4o-mini'])
