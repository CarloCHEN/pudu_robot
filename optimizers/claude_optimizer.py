import anthropic
import json
import os
from typing import Dict, List, Any
from dotenv import load_dotenv

class ClaudeOptimizer:
    """Handles Claude API interactions for work order optimization"""

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def optimize(self, prompt: str, optimization_level: str = "basic") -> Dict[str, Any]:
        """Send optimization request to Claude"""

        # Adjust parameters based on optimization level
        max_tokens = self._get_max_tokens(optimization_level)
        temperature = 0.1  # Low temperature for consistent optimization

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text

            # Try to parse JSON from response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1

                if json_start != -1 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    optimization_result = json.loads(json_str)

                    return {
                        "success": True,
                        "optimizations": optimization_result,
                        "raw_response": response_text,
                        "usage": {
                            "input_tokens": message.usage.input_tokens,
                            "output_tokens": message.usage.output_tokens,
                            "total_tokens": message.usage.input_tokens + message.usage.output_tokens
                        },
                        "optimization_level": optimization_level
                    }
                else:
                    return {
                        "success": False,
                        "error": "No valid JSON found in response",
                        "raw_response": response_text
                    }

            except json.JSONDecodeError as e:
                return {
                    "success": False,
                    "error": f"Failed to parse JSON: {e}",
                    "raw_response": response_text
                }

        except Exception as e:
            return {
                "success": False,
                "error": f"API call failed: {e}"
            }

    def _get_max_tokens(self, optimization_level: str) -> int:
        """Get appropriate max tokens based on optimization level"""
        token_limits = {
            "basic": 2000,
            "professional": 4000,
            "enterprise": 8000
        }
        return token_limits.get(optimization_level, 4000)