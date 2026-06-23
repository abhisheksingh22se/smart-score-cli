import json
from typing import Dict, Any

try:
    from tabulate import tabulate
except ImportError:
    # Minimal fallback in case tabulate fails to import
    def tabulate(rows, headers, tablefmt="simple"):
        col_widths = [max(len(str(x)) for x in col) for col in zip(*rows, headers)]
        row_format = " | ".join([f"{{:<{w}}}" for w in col_widths])
        table_str = row_format.format(*headers) + "\n" + "-+-".join(["-" * w for w in col_widths]) + "\n"
        for r in rows:
            table_str += row_format.format(*(str(x) for x in r)) + "\n"
        return table_str

class SmartScoreReport:
    """
    Formats the evaluation results into console-friendly Markdown tables or JSON strings.
    """

    @staticmethod
    def to_markdown(result: Dict[str, Any], benchmarks: Any) -> str:
        """
        Renders the final results as a clean Markdown report with a summary and detailed metric breakdown.
        """
        final_score = result["final_score"]
        grade = result["grade"]
        status = result["status"]
        
        # Color coding indicator for status
        indicator = "🟢 PASS"
        if status == "WARN":
            indicator = "🟡 WARN"
        elif status == "FAIL":
            indicator = "🔴 FAIL (DEPLOYMENT BLOCK)"

        # Summary Component Table
        summary_rows = [
            [" Security Score", f"{result['security_score']:.4f}", "60%"],
            [" Efficiency Score", f"{result['efficiency_score']:.4f}", "40%"],
            [" Final Composite Score", f"**{final_score:.4f}**", "100%"]
        ]
        summary_headers = ["Component", "Score (0-1)", "Weight"]
        summary_table = tabulate(summary_rows, headers=summary_headers, tablefmt="github")

        # Metrics Breakdown Table
        bm = benchmarks
        raw = result["metrics"]
        norm = result["normalized"]
        
        breakdown_rows = [
            ["Vulnerabilities (High) [V*]", f"{raw['V']}", f"{norm['V*']:.4f}", f"{bm.V}", "High-severity vulnerabilities (Lower is Better)"],
            ["Formal Verification Coverage [FVC+]", f"{raw['FVC']:.2f}%", f"{norm['FVC+']:.4f}", f"{bm.FVC}", "Formal verification coverage (Higher is Better)"],
            ["Invariant Violations [IV*]", f"{raw['IV']}", f"{norm['IV*']:.4f}", f"{bm.IV}", "Invariant violations count (Lower is Better)"],
            ["Avg Gas per Function [GF*]", f"{raw['GF']:.1f}", f"{norm['GF*']:.4f}", f"{bm.GF}", "Average function execution gas (Lower is Better)"],
            ["Gas Usage Variance [GV*]", f"{raw['GV']:.1f}", f"{norm['GV*']:.4f}", f"{bm.GV}", "Fluctuation in function gas costs (Lower is Better)"],
            ["Time Complexity [TC*]", f"{raw['TC']}", f"{norm['TC*']:.4f}", f"{bm.TC}", "Categorical loop complexity scaling (Lower is Better)"],
            ["Throughput [TP+]", f"{raw['TP']:.1f} tx/block", f"{norm['TP+']:.4f}", f"{bm.TP}", "Estimated transaction capacity (Higher is Better)"]
        ]
        breakdown_headers = ["Metric [Normalizer]", "Raw Value", "Normalized Score", "Historical Bounds [Min, Max]", "Research Description"]
        breakdown_table = tabulate(breakdown_rows, headers=breakdown_headers, tablefmt="github")

        report = f"""
# Smart Score Audit Report
Evaluate contract using the **Unified Security & Efficiency Evaluation Framework**.

## Executive Summary
{summary_table}

**Rating Result:** `{grade}`
**Status:** {indicator}

---

## Deep Dive Metric Analysis
{breakdown_table}
"""
        return report

    @staticmethod
    def to_json(result: Dict[str, Any]) -> str:
        """
        Renders the final results as an indented JSON string.
        """
        return json.dumps(result, indent=2)
