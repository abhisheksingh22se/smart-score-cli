// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Voting {
    struct Candidate {
        string name;
        uint voteCount;
    }

    address public admin;
    mapping(address => bool) public hasVoted;
    Candidate[] public candidates;

    constructor(string[] memory candidateNames) {
        admin = msg.sender;
        for (uint i = 0; i < candidateNames.length; i++) {
            candidates.push(Candidate({name: candidateNames[i], voteCount: 0}));
        }
    }

    function vote(uint candidateIndex) external {
        require(!hasVoted[msg.sender], "Already voted.");
        require(candidateIndex < candidates.length, "Invalid candidate.");
        hasVoted[msg.sender] = true;
        candidates[candidateIndex].voteCount++;
    }

    function getCandidate(uint index) external view returns (string memory name, uint voteCount) {
        require(index < candidates.length, "Invalid index.");
        Candidate memory c = candidates[index];
        return (c.name, c.voteCount);
    }

    function totalCandidates() external view returns (uint) {
        return candidates.length;
    }
}
