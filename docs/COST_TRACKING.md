# Cost Tracking Feature (Temporary)

This feature provides cost estimation for OpenAI API calls during blog generation to help estimate operational costs.

## What it tracks

- **Title Generation**: Cost of generating blog titles via OpenAI API
- **Research Phase**: Estimated cost for research agent LLM calls
- **Content Generation**: Estimated cost for content creation with images
- **Fact Checking**: Estimated cost for fact-checking agent calls
- **Finalization**: Estimated cost for final editing and formatting

## How it works

1. **Automatic Integration**: Cost tracking is automatically enabled when blog generation starts
2. **Token Estimation**: Uses content length and typical patterns to estimate token usage
3. **Current Pricing**: Based on OpenAI pricing as of 2024 (regularly updated pricing table)
4. **Console Output**: Prints detailed cost breakdown at the end of each blog generation

## Sample Output

```
============================================================
📊 BLOG GENERATION COST SUMMARY
============================================================
💰 Total Estimated Cost: $0.0234
🔢 Total Tokens: 12,847
   📥 Input Tokens: 5,200
   📤 Output Tokens: 7,647
⏱️  Duration: 45.2 seconds
📞 Total API Calls: 5

📱 Cost by Model:
   gpt-3.5-turbo: $0.0234 (12,847 tokens, 5 calls)

🔄 Cost by Phase:
   title_generation: $0.0003 (170 tokens, 1 calls)
   research_phase: $0.0067 (3,420 tokens, 1 calls)
   content_generation_phase: $0.0089 (4,567 tokens, 1 calls)
   fact_checking_phase: $0.0045 (2,890 tokens, 1 calls)
   finalization_phase: $0.0030 (1,800 tokens, 1 calls)

💡 Average cost per token: $0.000002
============================================================
```

## Easy Removal

To remove this feature completely:

1. **Remove cost tracking imports**:
   ```python
   # Remove this line from flows.py and main.py
   from .cost_tracker import CostTracker
   ```

2. **Remove cost tracking initialization**:
   ```python
   # Remove this line from BlogGenerationFlow.__init__
   self.cost_tracker = CostTracker("blog_generation")
   ```

3. **Remove cost estimation calls**:
   ```python
   # Remove these blocks from each phase
   self.cost_tracker.estimate_crew_cost(...)
   ```

4. **Remove cost summary printing**:
   ```python
   # Remove this block from finalization_phase
   print("\n" + "🔴" * 50)
   print("TEMPORARY COST TRACKING ENABLED")
   self.cost_tracker.print_cost_summary()
   print("🔴" * 50 + "\n")
   ```

5. **Delete the cost tracker file**:
   ```bash
   rm backend/src/bloggen/cost_tracker.py
   ```

## Notes

- **Estimation Only**: Costs are estimated based on content length and typical patterns
- **Pricing Updates**: Update `OPENAI_PRICING` in `cost_tracker.py` for current rates
- **No Impact**: Feature has no impact on blog generation functionality
- **Console Only**: Cost information is only printed to server console
