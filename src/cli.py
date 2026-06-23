import click
import os
import sys
import json
from typing import Optional

from .parser import SmartScoreParser
from .engine import SmartScoreEngine, BenchmarksConfig, RawMetrics
from .report import SmartScoreReport

def load_benchmarks_file(filepath: Optional[str]) -> BenchmarksConfig:
    """
    Loads custom benchmarks file, falling back to local config or class defaults.
    """
    default_config = BenchmarksConfig()
    
    if not filepath:
        # Try to resolve relative to cli.py
        cli_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.abspath(os.path.join(cli_dir, "..", "config", "benchmarks.json"))

    if not os.path.exists(filepath):
        print(f"ℹ️ Benchmarks config not found at '{filepath}'. Using default values.", file=sys.stderr)
        return default_config

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return BenchmarksConfig(**data)
    except Exception as e:
        print(f"⚠️ Failed to load benchmarks file: {e}. Falling back to defaults.", file=sys.stderr)
        return default_config

@click.command()
@click.option('--contract-path', '-c', type=click.Path(exists=False), default='contracts/Voting.sol',
              help='Path to target Solidity smart contract (used to estimate time complexity).')
@click.option('--slither-json', '-s', type=click.Path(exists=False), default='result/slither_output.json',
              help='Path to Slither JSON report.')
@click.option('--gas-json', '-g', type=click.Path(exists=False), default='hardhat_env/gasReporterOutput.json',
              help='Path to Hardhat gas reporter JSON output.')
@click.option('--fvc', '-f', type=float, default=0.0,
              help='Formal Verification Coverage percentage override (0.0 to 100.0).')
@click.option('--iv', '-i', type=int, default=None,
              help='Invariant Violations count override (falls back to Slither parser if not provided).')
@click.option('--gf', type=float, default=None,
              help='Average Function Gas override.')
@click.option('--gv', type=float, default=None,
              help='Gas Variance override.')
@click.option('--benchmarks', '-b', type=click.Path(exists=False), default=None,
              help='Path to custom benchmarks config JSON file.')
@click.option('--format', '-o', type=click.Choice(['markdown', 'json']), default='markdown',
              help='Output formatting: markdown (default) or json.')
@click.option('--fail-on-critical/--no-fail', default=True,
              help='Exit with status code 1 if final score is in Critical range (<0.40). Default is True.')
def cli(contract_path: str,
        slither_json: str,
        gas_json: str,
        fvc: float,
        iv: Optional[int],
        gf: Optional[float],
        gv: Optional[float],
        benchmarks: Optional[str],
        format: str,
        fail_on_critical: bool):
    """
    Smart Score CLI
    Evaluates Ethereum smart contracts against security and efficiency benchmarks in CI/CD pipelines.
    """
    # 1. Load configuration bounds
    benchmarks_config = load_benchmarks_file(benchmarks)

    # 2. Extract metrics via Parsers
    slither_metrics = SmartScoreParser.parse_slither_json(slither_json)
    gas_metrics = SmartScoreParser.parse_hardhat_gas(gas_json)
    tc_score = SmartScoreParser.estimate_time_complexity(contract_path)

    # 3. Assemble parameters, prioritizing explicit manual CLI overrides
    final_v = slither_metrics["V"]
    final_fvc = fvc
    
    # Invariant Violations override vs parser fallback
    final_iv = iv if iv is not None else slither_metrics["IV"]

    # Gas metrics: CLI override -> Hardhat parser -> default fallback values
    final_gf = gf if gf is not None else (gas_metrics["GF"] if gas_metrics["GF"] is not None else 33000.0)
    final_gv = gv if gv is not None else (gas_metrics["GV"] if gas_metrics["GV"] is not None else 3800.0)

    try:
        # Validate raw data structures via Pydantic model
        metrics = RawMetrics(
            V=final_v,
            FVC=final_fvc,
            IV=final_iv,
            GF=final_gf,
            GV=final_gv,
            TC=tc_score
        )
    except Exception as e:
        print(f" Input validation failed: {e}", file=sys.stderr)
        sys.exit(2)

    # 4. Execute calculations in the Engine
    engine = SmartScoreEngine(benchmarks_config)
    result = engine.evaluate(metrics)

    # 5. Format and present results
    if format == "markdown":
        report_output = SmartScoreReport.to_markdown(result, benchmarks_config)
        print(report_output)
    else:
        report_output = SmartScoreReport.to_json(result)
        print(report_output)

    # 6. Quality Gate enforcement
    if result["status"] == "FAIL":
        if fail_on_critical:
            print("\n [DEPLOYMENT BLOCK] Smart Score is Critical (< 0.40). Terminating workflow build.", file=sys.stderr)
            sys.exit(1)
        else:
            print("\n [WARNING] Smart Score is Critical (< 0.40) but bypass is enabled (--no-fail).", file=sys.stderr)

if __name__ == '__main__':
    cli()
