#!/bin/bash
set -e

# Suppress SSL warnings and set python path for the container
export PYTHONWARNINGS="ignore::DeprecationWarning"
export PYTHONPATH="/app"

# Usage parameters passed from Docker CMD or CLI
TARGET_CONTRACT="${1:-contracts/Voting.sol}"
FVC_OVERRIDE="${2:-0.0}"

if [ ! -f "$TARGET_CONTRACT" ]; then
  echo "❌ Error: Contract file '$TARGET_CONTRACT' not found inside container."
  exit 1
fi

CONTRACT_FILENAME=$(basename "$TARGET_CONTRACT")

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║             🎓 Smart Score Evaluator                     ║"
echo "║      (Containerized Web3 DevSecOps Pipeline)             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "📄 Target Contract : $CONTRACT_FILENAME"
echo "📊 FVC Override    : $FVC_OVERRIDE%"
echo ""

# Stage contract for Hardhat
echo "📁 [1/3] Staging contract for profiling..."
mkdir -p hardhat_env/contracts result
cp "$TARGET_CONTRACT" "hardhat_env/contracts/$CONTRACT_FILENAME"

# Slither static analysis
echo "🛡️  [2/3] Running Slither static analysis..."
rm -f result/slither_output.json

# We assume Slither is installed because the Dockerfile guarantees it
slither "$TARGET_CONTRACT" \
  --json result/slither_output.json \
  2>/dev/null || true

if [ ! -s "result/slither_output.json" ]; then
  echo "   ⚠️  Slither failed or produced no output. Creating empty report."
  echo '{"results": {"detectors": []}, "contracts": []}' > result/slither_output.json
else
  echo "   ✅ Slither analysis complete"
fi

# Hardhat gas profiling
echo "⚡ [3/3] Running Hardhat gas profiling..."
cd hardhat_env
npx hardhat clean > /dev/null 2>&1 || true
npx hardhat run profile.js --network hardhat 2>/dev/null
cd ..
echo "   ✅ Gas profiling complete"

# Smart Score evaluation
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🏆 Calculating Final Smart Score..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python3 -m src.cli \
  --contract-path "$TARGET_CONTRACT" \
  --slither-json  "result/slither_output.json" \
  --gas-json      "hardhat_env/gasReporterOutput.json" \
  --fvc           "$FVC_OVERRIDE" \
  --format        markdown

echo ""