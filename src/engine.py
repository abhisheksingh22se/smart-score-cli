from pydantic import BaseModel, Field, model_validator
from typing import Dict, Tuple, Any

class BenchmarksConfig(BaseModel):
    """
    Pydantic validator for historical benchmark min-max bounds.
    """
    V: Tuple[float, float] = Field(default=(0.0, 10.0))
    FVC: Tuple[float, float] = Field(default=(0.0, 100.0))
    IV: Tuple[float, float] = Field(default=(0.0, 10.0))
    GF: Tuple[float, float] = Field(default=(20000.0, 70000.0))
    GV: Tuple[float, float] = Field(default=(1000.0, 10000.0))
    TC: Tuple[float, float] = Field(default=(1.0, 5.0))
    TP: Tuple[float, float] = Field(default=(300.0, 1000.0))

    @model_validator(mode="before")
    @classmethod
    def check_min_max_bounds(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, list) or isinstance(val, tuple):
                    if len(val) == 2 and val[0] > val[1]:
                        raise ValueError(f"Benchmark boundary for '{key}' has min ({val[0]}) greater than max ({val[1]}).")
        return data


class RawMetrics(BaseModel):
    """
    Pydantic schema representing raw contract metrics.
    """
    V: int = Field(default=0, description="High-severity vulnerabilities")
    FVC: float = Field(default=0.0, description="Formal verification coverage (0.0 to 100.0)")
    IV: int = Field(default=0, description="Invariant violations count")
    GF: float = Field(default=33000.0, description="Average gas cost per function")
    GV: float = Field(default=3800.0, description="Gas usage variance")
    TC: int = Field(default=1, description="Categorical time complexity score (1 to 5)")
    TP: float = Field(default=0.0, description="Estimated throughput (block gas limit / GF)")

    @model_validator(mode="after")
    def calculate_throughput(self) -> 'RawMetrics':
        # Compute throughput dynamically if it is 0.0 or not set
        if self.TP == 0.0:
            block_gas_limit = 30000000.0  # Ethereum block gas limit
            self.TP = block_gas_limit / self.GF if self.GF > 0 else 0.0
        return self


class SmartScoreEngine:
    """
    Implements the scoring normalization, component aggregation, and quality gates logic.
    """
    def __init__(self, benchmarks: BenchmarksConfig):
        self.benchmarks = benchmarks

    @staticmethod
    def normalize(val: float, min_val: float, max_val: float) -> float:
        """
        Regular Min-Max normalization. Returns a float between 0.0 and 1.0.
        """
        if max_val == min_val:
            return 0.0
        norm = (val - min_val) / (max_val - min_val)
        return max(0.0, min(1.0, norm))

    @staticmethod
    def inverse_normalize(val: float, min_val: float, max_val: float) -> float:
        """
        Inverted Min-Max normalization. Returns a float between 0.0 and 1.0.
        """
        return 1.0 - SmartScoreEngine.normalize(val, min_val, max_val)

    def evaluate(self, metrics: RawMetrics) -> Dict[str, Any]:
        """
        Runs calculations to compute normalized metrics, sub-component scores,
        final composite score, and qualitative grade.
        """
        # --- Normalization ---
        norm_V = self.inverse_normalize(metrics.V, *self.benchmarks.V)
        norm_FVC = self.normalize(metrics.FVC, *self.benchmarks.FVC)
        norm_IV = self.inverse_normalize(metrics.IV, *self.benchmarks.IV)

        norm_GF = self.inverse_normalize(metrics.GF, *self.benchmarks.GF)
        norm_GV = self.inverse_normalize(metrics.GV, *self.benchmarks.GV)
        norm_TC = self.inverse_normalize(metrics.TC, *self.benchmarks.TC)
        norm_TP = self.normalize(metrics.TP, *self.benchmarks.TP)

        # --- Component Scoring ---
        # S = (0.5 * V*) + (0.3 * FVC+) + (0.2 * IV*)
        security_score = (0.5 * norm_V) + (0.3 * norm_FVC) + (0.2 * norm_IV)

        # E = (0.35 * GF*) + (0.25 * GV*) + (0.25 * TC) + (0.15 * TP+)
        efficiency_score = (0.35 * norm_GF) + (0.25 * norm_GV) + (0.25 * norm_TC) + (0.15 * norm_TP)

        # --- Composite Scoring ---
        # Final Score = (0.6 * S) + (0.4 * E)
        final_score = (0.6 * security_score) + (0.4 * efficiency_score)

        # Determine qualitative grade
        if final_score >= 0.90:
            grade = "Excellent"
            status = "PASS"
        elif final_score >= 0.75:
            grade = "Good"
            status = "PASS"
        elif final_score >= 0.60:
            grade = "Fair"
            status = "PASS"
        elif final_score >= 0.40:
            grade = "Poor"
            status = "WARN"
        else:
            grade = "Critical"
            status = "FAIL"

        return {
            "metrics": {
                "V": metrics.V,
                "FVC": metrics.FVC,
                "IV": metrics.IV,
                "GF": metrics.GF,
                "GV": metrics.GV,
                "TC": metrics.TC,
                "TP": metrics.TP
            },
            "normalized": {
                "V*": round(norm_V, 4),
                "FVC+": round(norm_FVC, 4),
                "IV*": round(norm_IV, 4),
                "GF*": round(norm_GF, 4),
                "GV*": round(norm_GV, 4),
                "TC*": round(norm_TC, 4),
                "TP+": round(norm_TP, 4)
            },
            "security_score": round(security_score, 4),
            "efficiency_score": round(efficiency_score, 4),
            "final_score": round(final_score, 4),
            "grade": grade,
            "status": status
        }
