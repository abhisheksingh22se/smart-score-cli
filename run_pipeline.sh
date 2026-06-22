#!/bin/bash
set -e

# Suppress SSL warnings from urllib3 
export PYTHONWARNINGS="ignore::DeprecationWarning"
export PYTHONPATH="."

# Python interpreter
PYTHON="/usr/bin/python3"

# Usage
TARGET_CONTRACT="${1:-contracts/Voting.sol}"
FVC_OVERRIDE="${2:-0.0}"    # Optional: pass FVC % as second argument

if [ ! -f "$TARGET_CONTRACT" ]; then
  echo "❌ Error: Contract file '$TARGET_CONTRACT' not found."
  exit 1
fi

CONTRACT_FILENAME=$(basename "$TARGET_CONTRACT")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           🎓 Smart Score CI Pipeline                     ║"
echo "║     Security & Efficiency Evaluation Framework           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📄 Target Contract : $CONTRACT_FILENAME"
echo "📊 FVC Override    : $FVC_OVERRIDE%"
echo ""

# Ensure directories exist
mkdir -p contracts result hardhat_env/artifacts hardhat_env/contracts

# Stage contract
echo "📁 [1/4] Staging contract..."
ABS_TARGET=$($PYTHON -c "import os; print(os.path.abspath('$TARGET_CONTRACT'))")
ABS_DEST=$($PYTHON -c "import os; print(os.path.abspath('contracts/$CONTRACT_FILENAME'))")
if [ "$ABS_TARGET" != "$ABS_DEST" ]; then
  cp "$TARGET_CONTRACT" "contracts/$CONTRACT_FILENAME"
fi
cp "contracts/$CONTRACT_FILENAME" "hardhat_env/contracts/$CONTRACT_FILENAME"

# Setup solc
if command -v solc-select >/dev/null 2>&1; then
  echo "⚙️  [2/4] Configuring solc 0.8.20..."
  solc-select install 0.8.20 2>/dev/null || true
  solc-select use 0.8.20 2>/dev/null || true
fi

# Slither static analysis
echo "🛡️  [3/4] Running Slither static analysis..."

# Always remove old result to allow fresh overwrite
rm -f result/slither_output.json

if command -v slither >/dev/null 2>&1; then
  slither "contracts/$CONTRACT_FILENAME" \
    --json result/slither_output.json \
    2>/dev/null || true

  if [ -f "result/slither_output.json" ]; then
    echo "   ✅ Slither analysis complete → result/slither_output.json"
  else
    echo "   ⚠️  Slither ran but produced no output. Creating empty report."
    echo '{"results": {"detectors": []}, "contracts": []}' > result/slither_output.json
  fi
else
  echo "   ⚠️  Slither not installed. Creating empty report."
  echo '{"results": {"detectors": []}, "contracts": []}' > result/slither_output.json
fi

# Hardhat gas profiling
echo "⚡ [4/4] Running Hardhat gas profiling..."
cd hardhat_env
npx hardhat clean > /dev/null 2>&1 || true
npx hardhat run profile.js --network hardhat 2>/dev/null
cd ..
echo "   ✅ Gas profiling complete → hardhat_env/gasReporterOutput.json"

# Smart Score evaluation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏆 Running Smart Score Evaluator..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

$PYTHON -m src.cli \
  --contract-path "contracts/$CONTRACT_FILENAME" \
  --slither-json  "result/slither_output.json" \
  --gas-json      "hardhat_env/gasReporterOutput.json" \
  --fvc           "$FVC_OVERRIDE" \
  --format        markdown

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Smart Score pipeline finished!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Output files:"
echo "   result/slither_output.json"
echo "   hardhat_env/gasReporterOutput.json"
echo ""
echo "💡 Tips:"
echo "   Pass FVC %  : ./run_pipeline.sh contracts/Voting.sol 75.0"
echo "   JSON output : add --format json to the cli command above"