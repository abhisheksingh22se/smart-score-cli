const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

function getMockArgValue(input, fallbackAddress) {
  const type = input.type;
  
  // Handle structs/tuples
  if (type === "tuple" && input.components) {
    const structObj = {};
    for (const comp of input.components) {
      structObj[comp.name] = getMockArgValue(comp, fallbackAddress);
    }
    return structObj;
  }
  
  // Handle arrays
  if (type.endsWith("[]")) {
    const baseType = type.slice(0, -2);
    const elementMock = getMockArgValue({ type: baseType, components: input.components }, fallbackAddress);
    return [elementMock];
  }
  
  // Handle basic types
  if (type.startsWith("uint") || type.startsWith("int")) {
    return 0;
  } else if (type === "address") {
    return fallbackAddress;
  } else if (type === "bool") {
    return false;
  } else if (type === "string") {
    return "test";
  } else if (type.startsWith("bytes")) {
    return "0x00";
  } else {
    return "0x00";
  }
}

function getMockArgs(inputs, fallbackAddress) {
  if (!inputs) return [];
  return inputs.map(input => getMockArgValue(input, fallbackAddress));
}

async function main() {
  console.log("Compiling contracts...");
  await hre.run("compile");

  // Get compiled artifacts paths
  const artifactsPath = path.join(__dirname, "artifacts", "contracts");
  if (!fs.existsSync(artifactsPath)) {
    console.error("No compiled contracts found in artifacts/contracts.");
    process.exit(1);
  }

  // Find all contract JSON artifacts recursively (excluding debug files)
  const getFiles = (dir) => {
    let files = [];
    if (!fs.existsSync(dir)) return files;
    const list = fs.readdirSync(dir);
    for (const file of list) {
      const fullPath = path.join(dir, file);
      const stat = fs.statSync(fullPath);
      if (stat.isDirectory()) {
        files = files.concat(getFiles(fullPath));
      } else if (file.endsWith(".json") && !file.endsWith(".dbg.json")) {
        files.push(fullPath);
      }
    }
    return files;
  };

  const artifactFiles = getFiles(artifactsPath);
  const gasReport = {
    data: {
      methods: {}
    }
  };

  const [deployer] = await hre.ethers.getSigners();
  console.log(`Using deployer address: ${deployer.address}`);

  for (const artifactFile of artifactFiles) {
    const artifact = JSON.parse(fs.readFileSync(artifactFile, "utf8"));
    const contractName = artifact.contractName;
    const abi = artifact.abi;
    
    // Skip libraries or interfaces without bytecode
    if (!artifact.bytecode || artifact.bytecode === "0x") {
      continue;
    }

    console.log(`\nProfiling contract: ${contractName}`);

    let contractFactory;
    try {
      contractFactory = await hre.ethers.getContractFactory(contractName);
    } catch (e) {
      console.log(`Skipping ${contractName}: ${e.message}`);
      continue;
    }

    // Try to deploy
    const constructorAbi = abi.find(item => item.type === 'constructor');
    const deployArgs = constructorAbi ? getMockArgs(constructorAbi.inputs, deployer.address) : [];

    let contract;
    try {
      contract = await contractFactory.deploy(...deployArgs);
      if (typeof contract.waitForDeployment === "function") {
        await contract.waitForDeployment();
      } else if (typeof contract.deployed === "function") {
        await contract.deployed();
      }
      
      const addr = contract.target || contract.address || (typeof contract.getAddress === "function" ? await contract.getAddress() : "unknown");
      console.log(`Deployed ${contractName} to: ${addr}`);
    } catch (e) {
      console.error(`Failed to deploy ${contractName}: ${e.message}`);
      continue;
    }

    // Profile state-changing functions (exclude view, pure, and constructor)
    const functionsToProfile = abi.filter(item => 
      item.type === 'function' && 
      item.stateMutability !== 'view' && 
      item.stateMutability !== 'pure'
    );

    for (const func of functionsToProfile) {
      const funcName = func.name;
      const mockArgs = getMockArgs(func.inputs, deployer.address);
      
      let gasUsed = 30000; // default fallback
      try {
        // Try estimating gas first
        const gasEstimate = await contract[funcName].estimateGas(...mockArgs);
        gasUsed = Number(gasEstimate);
        
        // Actually execute transaction to record actual receipt gas
        const tx = await contract[funcName](...mockArgs);
        const receipt = await tx.wait();
        gasUsed = Number(receipt.gasUsed);
      } catch (e) {
        console.log(` - Note: Call to function ${funcName} reverted/failed: ${e.message.split('\n')[0]}. Using estimated/fallback gas.`);
        try {
          const gasEst = await contract[funcName].estimateGas(...mockArgs);
          gasUsed = Number(gasEst);
        } catch (_) {}
      }

      console.log(` - Function: ${funcName}() -> Gas Used: ${gasUsed}`);

      const key = `${funcName}`;
      if (!gasReport.data.methods[key]) {
        gasReport.data.methods[key] = { gasData: [] };
      }
      gasReport.data.methods[key].gasData.push(gasUsed);
    }
  }

  // Save the report
  const outputPath = path.join(__dirname, "gasReporterOutput.json");
  fs.writeFileSync(outputPath, JSON.stringify(gasReport, null, 2));
  console.log(`\nGas profiling complete. Report saved to ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
