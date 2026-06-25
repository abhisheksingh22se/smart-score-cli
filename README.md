# 🛡️ Smart Score CLI & GitHub Action

A **Web3 DevSecOps** evaluation tool that audits Solidity smart contracts by integrating **Security** and **Efficiency** metrics into a unified composite score — fully automatable in CI/CD pipelines.

Based on original research from:
1. *"Smart Contract Measurement Methodology: Extracting and Analyzing Key Performance Indicators"*
2. *"Smart Contract Scoring Framework: Integrating Security and Efficiency Metrics into a Unified Evaluation Model"*

---

## 📁 Project Structure

```
smart-score-cli/
├── .github/workflows/audit.yml    # GitHub Actions CI/CD workflow
├── config/benchmarks.json         # Historical min-max bounds for normalization
├── contracts/Voting.sol           # Example Solidity smart contract
├── hardhat_env/                   # Hardhat project for gas profiling
├── src/
│   ├── __init__.py
│   ├── cli.py                     # CLI entrypoint
│   ├── engine.py                  # Pydantic models + scoring formulas
│   ├── parser.py                  # Slither + Hardhat artifact parsers
│   └── report.py                  # Markdown + JSON report formatters
├── action.yml                     # Reusable GitHub Action definition
├── Dockerfile                     # Multi-stage container build
├── docker-compose.yml             # Local container orchestration
├── requirements.txt
└── run_pipeline.sh                # Local + container pipeline runner
```

---

## 📈 Scoring Methodology

### Normalization Layer

**Regular** — higher is better (e.g. Formal Verification Coverage):
$$x^* = \frac{x - x_{min}}{x_{max} - x_{min}}$$

**Inverted** — lower is better (e.g. Vulnerabilities, Gas Costs):
$$x^* = 1 - \frac{x - x_{min}}{x_{max} - x_{min}}$$

### Component Scores

$$S = (0.5 \cdot V^{\ast}) + (0.3 \cdot FVC^{\ast}) + (0.2 \cdot IV^{\ast})$$

$$E = (0.35 \cdot GF^{\ast}) + (0.25 \cdot GV^{\ast}) + (0.25 \cdot TC^{\ast}) + (0.15 \cdot TP^{\ast})$$

### Final Composite Score & Quality Gates

$$\text{Final Score} = (0.6 \cdot S) + (0.4 \cdot E)$$

| Score Range | Grade | Status | Pipeline Behavior |
|:---|:---|:---|:---|
| ≥ 0.90 | `Excellent` | `PASS` | Deployment allowed |
| 0.75 – 0.89 | `Good` | `PASS` | Deployment allowed |
| 0.60 – 0.74 | `Fair` | `PASS` | Review recommended |
| 0.40 – 0.59 | `Poor` | `WARN` | Allowed with warnings |
| < 0.40 | `Critical` | `FAIL` | **Deployment blocked** — exits code `1` |

---

## 🚀 Quickstart

### Option A — Local Shell

```bash
# install dependencies
pip install -r requirements.txt
solc-select install 0.8.20 && solc-select use 0.8.20
cd hardhat_env && npm install && cd ..

# run pipeline
./run_pipeline.sh contracts/Voting.sol

# with Formal Verification Coverage override
./run_pipeline.sh contracts/Voting.sol 75.0
```

### Option B — Docker

```bash
# build
docker build -t smart-score-cli:latest .

# run
docker run --rm \
  -v $(pwd)/contracts:/app/contracts \
  -v $(pwd)/result:/app/result \
  smart-score-cli:latest contracts/Voting.sol 75.0

# or with docker-compose
docker-compose up
```

### Option C — CLI Directly

```bash
python3 -m src.cli \
  --contract-path contracts/Voting.sol \
  --slither-json  result/slither_output.json \
  --gas-json      hardhat_env/gasReporterOutput.json \
  --fvc           75.0 \
  --format        markdown
```

---

## 🐳 Docker Multi-Stage Build

```
Stage 1: builder
├── Install build tools + Node.js
├── pip install dependencies
└── npm ci (Hardhat)
        │
        └── COPY --from=builder
                │
Stage 2: runtime
├── Node.js + git only
├── Python packages (from builder)
├── Hardhat node_modules (from builder)
├── solc-select + solc 0.8.20
└── Project source
```

Build tools are discarded in the final image — smaller size, reduced attack surface.

---

## ⚙️ CLI Reference

| Option | Description | Default |
|:---|:---|:---|
| `-c, --contract-path` | Path to Solidity contract | `contracts/Voting.sol` |
| `-s, --slither-json` | Path to Slither JSON report | `result/slither_output.json` |
| `-g, --gas-json` | Path to Hardhat gas report | `hardhat_env/gasReporterOutput.json` |
| `-f, --fvc` | Formal Verification Coverage % | `0.0` |
| `-i, --iv` | Invariant Violations override | — |
| `--gf` | Avg Gas per Function override | — |
| `--gv` | Gas Variance override | — |
| `-b, --benchmarks` | Path to custom benchmarks.json | built-in |
| `-o, --format` | `markdown` or `json` | `markdown` |
| `--fail-on-critical / --no-fail` | Block pipeline if score < 0.40 | `True` |

---

## 🐙 GitHub Action Integration

Add to `.github/workflows/audit.yml` in your repo. The workflow:
1. Runs **Slither** static analysis → `result/slither_output.json`
2. Runs **Hardhat** gas profiling → `hardhat_env/gasReporterOutput.json`
3. Calls this action → calculates and outputs the Smart Score

```yaml
- name: Run Smart Score Evaluator
  id: smart-score
  uses: YOUR_ORG/smart-score-cli@main
  with:
    contract-path: 'contracts/Voting.sol'
    slither-json-path: 'result/slither_output.json'
    gas-report-json-path: 'hardhat_env/gasReporterOutput.json'
    fvc: '80.0'
    fail-on-critical: 'true'
```

### Action Inputs

| Input | Description | Default |
|:---|:---|:---|
| `contract-path` | Path to Solidity contract | `contracts/Voting.sol` |
| `slither-json-path` | Slither JSON report path | `result/slither_output.json` |
| `gas-report-json-path` | Hardhat gas report path | `hardhat_env/gasReporterOutput.json` |
| `fvc` | Formal Verification Coverage % | `0.0` |
| `fail-on-critical` | Block pipeline if Critical | `true` |

### Action Outputs

| Output | Description |
|:---|:---|
| `score` | Final composite score (0.0–1.0) |
| `grade` | Qualitative grade |
| `security-score` | Security sub-score |
| `efficiency-score` | Efficiency sub-score |

---

## 📊 Example Output

```
# Smart Score Audit Report

## Executive Summary

| Component             | Score (0-1) | Weight |
|-----------------------|-------------|--------|
| Security Score        | 0.7000      | 60%    |
| Efficiency Score      | 0.5387      | 40%    |
| Final Composite Score | **0.6355**  | 100%   |

Rating Result: `Fair`
Status: 🟢 PASS
```

---

## 🔧 Benchmarks Configuration

Customize normalization bounds in `config/benchmarks.json`:

```json
{
  "V":   [0, 10],
  "FVC": [0.0, 100.0],
  "IV":  [0, 10],
  "GF":  [20000, 70000],
  "GV":  [1000, 10000],
  "TC":  [1, 5],
  "TP":  [300, 1000]
}
```

Pass a custom file at runtime: `--benchmarks path/to/benchmarks.json`

---

## 📦 Dependencies

| Tool | Purpose |
|:---|:---|
| `click` | CLI argument parsing |
| `pydantic` | Data validation |
| `tabulate` | Markdown table formatting |
| `slither-analyzer` | Static vulnerability analysis |
| `solc-select` | Solidity compiler management |
| `hardhat` | Gas profiling |

---

## 🤝 Contributing

```bash
git checkout -b feature/your-feature
git commit -m "feat: describe your change"
git push origin feature/your-feature
```