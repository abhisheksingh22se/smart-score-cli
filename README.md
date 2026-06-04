# 🛡️ Smart Score CLI & GitHub Action

Evaluating Solidity smart contracts by integrating **Security** and **Efficiency** metrics into a single unified scoring system. 

Based on research from the thesis papers:
1. *"Smart Contract Measurement Methodology: Extracting and Analyzing Key Performance Indicators"*
2. *"Smart Contract Scoring Framework: Integrating Security and Efficiency Metrics into a Unified Evaluation Model"*

---

## 📈 Scoring Methodology & Mathematics

The evaluation framework measures contracts across two core dimensions:

### 1. Normalization Layer
All raw metrics are normalized between `0.0` and `1.0` using min-max historical bounds:
* **Regular Normalization** (higher is better, e.g., Formal Verification Coverage):
  $$x^* = \frac{x - x_{min}}{x_{max} - x_{min}}$$
* **Inverted Normalization** (lower is better, e.g., Vulnerability Counts, Gas Costs, Invariant Violations):
  $$x^* = 1 - \frac{x - x_{min}}{x_{max} - x_{min}}$$
* Normalized metrics are clipped to $[0.0, 1.0]$ to prevent boundary spillover.

### 2. Component Scoring Equations
* **Security Score ($S$)**:
  $$S = (0.5 \cdot V^*) + (0.3 \cdot FVC^+) + (0.2 \cdot IV^*)$$
  * $V^*$: Inverted normalized high-severity vulnerability count
  * $FVC^+$: Normalized formal verification coverage percentage (e.g. 0-100)
  * $IV^*$: Inverted normalized invariant violations (unreachable statements)
* **Efficiency Score ($E$)**:
  $$E = (0.35 \cdot GF^*) + (0.25 \cdot GV^*) + (0.25 \cdot TC^*) + (0.15 \cdot TP^+)$$
  * $GF^*$: Inverted normalized average function gas
  * $GV^*$: Inverted normalized variance of gas costs
  * $TC^*$: Normalized categorical complexity rating (1-5 range)
  * $TP^+$: Normalized throughput (derived as $\frac{\text{Block Gas Limit}}{GF}$)

### 3. Final Composite Score & Quality Gates
$$\text{Final Score} = (0.6 \cdot S) + (0.4 \cdot E)$$

| Final Score Range | Grade | Action Status | Build Pipeline Behavior |
| :--- | :--- | :--- | :--- |
| $\ge 0.90$ | `Excellent` | `PASS` | Allowed to proceed. |
| $0.75 - 0.89$ | `Good` | `PASS` | Allowed to proceed (Production Suitable). |
| $0.60 - 0.74$ | `Fair` | `PASS` | Allowed to proceed (Review Recommended). |
| $0.40 - 0.59$ | `Poor` | `WARN` | Allowed to proceed with warnings. |
| $< 0.40$ | `Critical` | `FAIL` | **Blocked** (CLI exits with code `1`). |

---

## 🛠️ CLI Usage & Instructions

### Installation

Install dependencies locally using python:
```bash
cd smart-score-cli
pip install -r requirements.txt
```

### Running Locally

Execute the tool using the module flag:
```bash
python3 -m src.cli --contract-path contracts/Voting.sol \
                   --slither-json result/slither_output.json
```

### CLI CLI Parameter reference:
```
Options:
  -c, --contract-path PATH      Path to target Solidity smart contract (used to
                                estimate time complexity). Default:
                                contracts/Voting.sol
  -s, --slither-json PATH       Path to Slither JSON report. Default:
                                result/slither_output.json
  -g, --gas-json PATH           Path to Hardhat gas reporter JSON output.
                                Default: hardhat_env/gasReporterOutput.json
  -f, --fvc FLOAT               Formal Verification Coverage percentage override
                                (0.0 to 100.0). Default: 0.0
  -i, --iv INTEGER              Invariant Violations count override.
  --gf FLOAT                    Average Function Gas override.
  --gv FLOAT                    Gas Variance override.
  -b, --benchmarks PATH         Path to custom benchmarks config JSON file.
  -o, --format [markdown|json]  Output formatting: markdown (default) or json.
  --fail-on-critical / --no-fail
                                Exit with status code 1 if final score is in
                                Critical range (<0.40). Default is True.
```

---

## 🐙 GitHub Action CI/CD Integration

Integrate the evaluator directly in your automated validation workflows (`.github/workflows/audit.yml`):

```yaml
name: Smart Contract Scoring Audit

on: [push, pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      # Setup Slither & compile contracts
      - name: Run Slither Analyzer
        uses: crytic/slither-action@v0.11.0
        continue-on-error: true
        with:
          target: 'contracts/'
          json: 'result/slither_output.json'

      # Run smart score CLI
      - name: Run Smart Score Evaluator
        uses: ./smart-score-cli
        with:
          contract-path: 'contracts/Voting.sol'
          slither-json-path: 'result/slither_output.json'
          gas-report-json-path: 'hardhat_env/gasReporterOutput.json'
          fvc: '80.0' # Passed from symbolic tests or verification coverage
          fail-on-critical: 'true'
```
