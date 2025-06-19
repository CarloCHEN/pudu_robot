from datetime import datetime
import json

from generators.work_order_generator import WorkOrderGenerator
from processors.context_builder import ContextBuilder
from processors.prompt_builder import PromptBuilder
from optimizers.claude_optimizer import ClaudeOptimizer
from formatters.result_formatter import ResultFormatter
from utils.tier_validator import TierValidator

def main():
    """Enhanced main entry point with tier management"""

    print("🚀 Work Order Optimization System")
    print("=" * 50)

    # Enhanced Configuration with tier management
    num_work_orders = 25
    optimization_level = "enterprise"  # basic, professional, enterprise
    customer_tier = "enterprise"       # NEW: Customer's actual subscription tier
    optimization_focus = "all"           # time, assignee, priority, location, all
    output_format = "summary"            # summary, detailed, json
    monthly_usage = 15                   # NEW: How many optimizations used this month

    print(f"📋 Generating {num_work_orders} synthetic work orders...")

    # Step 1: Validate tier access before processing
    tier_validator = TierValidator()
    validation = tier_validator.validate_optimization_request(
        customer_tier, optimization_level, num_work_orders, monthly_usage
    )

    if not validation["valid"]:
        print(f"❌ Access Denied: {validation['message']}")
        if validation.get("upgrade_required"):
            print(f"💳 Upgrade at: {validation.get('upgrade_url', '/upgrade')}")
        return

    # Show cost information
    cost_info = validation["cost_info"]
    if cost_info["billing_type"] == "included":
        print(f"💰 Cost: Included ({cost_info['remaining_included']} remaining this month)")
    else:
        print(f"💰 Cost: ${cost_info['total_cost']:.2f}")

    # Step 2: Generate synthetic work orders
    generator = WorkOrderGenerator()
    work_orders = generator.generate_work_orders(num_work_orders)

    print(f"✅ Generated {len(work_orders)} work orders")
    print(f"👤 Customer Tier: {customer_tier}")
    print(f"🎯 Optimization Level: {optimization_level}")
    print(f"🔍 Focus: {optimization_focus}")
    print("")

    # Step 3: Build context with tier awareness
    print("🔍 Analyzing work orders and building context...")
    context_builder = ContextBuilder(WorkOrderGenerator())  # NEW: Tier-aware builder
    context = context_builder.build_context(
        work_orders,
        optimization_level=optimization_level,
        focus=optimization_focus,
        customer_tier=customer_tier  # NEW: Pass customer tier
    )

    # Check for validation errors
    if context.get("error"):
        print(f"❌ Context building failed: {context['message']}")
        return

    # Step 4: Build optimization prompt
    print("📝 Building optimization prompt...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build_optimization_prompt(context)

    print(f"📊 Estimated prompt length: ~{len(prompt)} characters")
    print("")

    # print(prompt)

    # Step 5: Call Claude API for optimization
    print("🤖 Calling Claude API for optimization...")
    optimizer = ClaudeOptimizer()
    results = optimizer.optimize(prompt, optimization_level)

    # Add cost info to results
    if results.get("success"):
        results["optimizations"]["cost_info"] = cost_info

    # Step 6: Format and display results with tier awareness
    print("")
    formatter = ResultFormatter()
    formatted_results = formatter.format_optimization_results(
        results, output_format, customer_tier
    )

    print(formatted_results)

    # Optional: Save detailed results to file
    if results.get("success"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimization_results_{customer_tier}_{timestamp}.json"

        # Add tier metadata to saved results
        results["tier_metadata"] = {
            "customer_tier": customer_tier,
            "optimization_level": optimization_level,
            "cost_info": cost_info,
            "validation_info": validation
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"💾 Detailed results saved to: {filename}")

if __name__ == "__main__":
    main()