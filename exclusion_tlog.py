"""
Exclusion Transparency Log

A novel transparency log data structure based on recursively merged ordered merkle trees.
Because the merkle tree leaves are in sorted order, we can construct exclusion proofs
(proofs that a value is NOT in the log).

The key insight is that if leaves are sorted, we can prove non-membership by showing
the gap between two consecutive values where the target would have to be.
"""

import hashlib
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass
import json


@dataclass
class MerkleNode:
    """
    A node in the merkle tree.
    
    For leaf nodes: value is the actual data, left and right are None
    For internal nodes: value is None, left and right are child nodes
    """
    hash: bytes
    value: Optional[Any] = None
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    
    @property
    def is_leaf(self) -> bool:
        return self.value is not None


@dataclass
class InclusionProof:
    """
    Proof that a value is included in the tree.
    Contains the value and the sibling hashes needed to recompute the root.
    """
    value: Any
    leaf_hash: bytes
    sibling_hashes: List[Tuple[bytes, bool]]  # (hash, is_left_sibling)
    root_hash: bytes
    
    def verify(self) -> bool:
        """Verify this inclusion proof."""
        current = self.leaf_hash
        for sibling_hash, is_left in self.sibling_hashes:
            if is_left:
                current = hash_pair(sibling_hash, current)
            else:
                current = hash_pair(current, sibling_hash)
        return current == self.root_hash


@dataclass
class ExclusionProof:
    """
    Proof that a value is NOT included in the tree.
    
    Because leaves are sorted, we prove non-membership by showing the gap
    between two consecutive values where the target would have to be.
    """
    target: Any
    predecessor: Optional[Any]  # None if target would be before all values
    successor: Optional[Any]    # None if target would be after all values
    predecessor_proof: Optional[InclusionProof]
    successor_proof: Optional[InclusionProof]
    root_hash: bytes
    
    def verify(self) -> bool:
        """
        Verify this exclusion proof.
        
        The proof is valid if:
        1. The predecessor and successor inclusion proofs are valid
        2. predecessor < target < successor (in sorted order)
        3. The values are consecutive in the sorted tree
        """
        # Verify inclusion proofs
        if self.predecessor_proof and not self.predecessor_proof.verify():
            return False
        if self.successor_proof and not self.successor_proof.verify():
            return False
        
        # Verify ordering
        if self.predecessor is not None and self.predecessor >= self.target:
            return False
        if self.successor is not None and self.successor <= self.target:
            return False
        
        # Verify they point to the same root
        if self.predecessor_proof and self.predecessor_proof.root_hash != self.root_hash:
            return False
        if self.successor_proof and self.successor_proof.root_hash != self.root_hash:
            return False
        
        return True


def hash_value(value: Any) -> bytes:
    """Hash a leaf value."""
    if isinstance(value, bytes):
        data = value
    elif isinstance(value, str):
        data = value.encode('utf-8')
    else:
        data = json.dumps(value, sort_keys=True).encode('utf-8')
    return hashlib.sha256(b'LEAF:' + data).digest()


def hash_pair(left: bytes, right: bytes) -> bytes:
    """Hash a pair of child hashes to create a parent hash."""
    return hashlib.sha256(b'NODE:' + left + right).digest()


class ExclusionTLog:
    """
    Exclusion Transparency Log
    
    A transparency log that supports both inclusion and exclusion proofs.
    Based on recursively merged ordered merkle trees.
    
    The tree is built by:
    1. Sorting all values
    2. Creating leaf nodes for each value
    3. Recursively merging pairs of nodes/trees until we have a single root
    
    Because leaves are sorted, we can prove non-membership efficiently.
    """
    
    def __init__(self, values: Optional[List[Any]] = None):
        """
        Initialize the transparency log.
        
        Args:
            values: Optional list of initial values to include
        """
        self.root: Optional[MerkleNode] = None
        self.sorted_values: List[Any] = []
        
        if values:
            self.build(values)
    
    def build(self, values: List[Any]) -> None:
        """
        Build the merkle tree from a list of values.
        
        Args:
            values: List of values to include in the tree
        """
        if not values:
            self.root = None
            self.sorted_values = []
            return
        
        # Sort values for ordered tree property
        self.sorted_values = sorted(values)
        
        # Create leaf nodes
        leaves = [
            MerkleNode(hash=hash_value(val), value=val)
            for val in self.sorted_values
        ]
        
        # Recursively merge to build tree
        self.root = self._merge_nodes(leaves)
    
    def _merge_nodes(self, nodes: List[MerkleNode]) -> MerkleNode:
        """
        Recursively merge nodes into a binary tree.
        
        Args:
            nodes: List of nodes to merge
            
        Returns:
            Root node of the merged tree
        """
        if len(nodes) == 1:
            return nodes[0]
        
        # Pair up nodes and create parent nodes
        parents = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                # We have a pair
                left = nodes[i]
                right = nodes[i + 1]
                parent = MerkleNode(
                    hash=hash_pair(left.hash, right.hash),
                    left=left,
                    right=right
                )
                parents.append(parent)
            else:
                # Odd one out, promote it
                parents.append(nodes[i])
        
        # Recursively merge parents
        return self._merge_nodes(parents)
    
    def get_root_hash(self) -> Optional[bytes]:
        """Get the root hash of the tree."""
        return self.root.hash if self.root else None
    
    def contains(self, value: Any) -> bool:
        """Check if a value is in the tree."""
        return value in self.sorted_values
    
    def prove_inclusion(self, value: Any) -> Optional[InclusionProof]:
        """
        Generate an inclusion proof for a value.
        
        Args:
            value: The value to prove inclusion for
            
        Returns:
            InclusionProof if value is in tree, None otherwise
        """
        if value not in self.sorted_values:
            return None
        
        leaf_hash = hash_value(value)
        sibling_hashes = []
        
        # Find the leaf index
        leaf_idx = self.sorted_values.index(value)
        
        # Collect sibling hashes on path to root
        self._collect_siblings(self.root, leaf_idx, len(self.sorted_values), sibling_hashes)
        
        # Reverse to get bottom-up order (leaf to root)
        sibling_hashes.reverse()
        
        return InclusionProof(
            value=value,
            leaf_hash=leaf_hash,
            sibling_hashes=sibling_hashes,
            root_hash=self.root.hash
        )
    
    def _collect_siblings(self, node: MerkleNode, target_idx: int, total_leaves: int, 
                         siblings: List[Tuple[bytes, bool]], current_start: int = 0) -> bool:
        """
        Collect sibling hashes on the path from a leaf to the root.
        
        Args:
            node: Current node being examined
            target_idx: Index of the target leaf in sorted order
            total_leaves: Total number of leaves in tree
            siblings: List to append sibling hashes to
            current_start: Starting index of leaves under this node
            
        Returns:
            True if target was found in this subtree
        """
        if node.is_leaf:
            return current_start == target_idx
        
        # Calculate split point
        left_size = self._subtree_size(node.left)
        
        # Check which subtree contains our target
        if target_idx < current_start + left_size:
            # Target is in left subtree
            if node.right:
                siblings.append((node.right.hash, False))
            return self._collect_siblings(node.left, target_idx, total_leaves, siblings, current_start)
        else:
            # Target is in right subtree
            if node.left:
                siblings.append((node.left.hash, True))
            return self._collect_siblings(node.right, target_idx, total_leaves, siblings, 
                                        current_start + left_size)
    
    def _subtree_size(self, node: Optional[MerkleNode]) -> int:
        """Count the number of leaves in a subtree."""
        if node is None:
            return 0
        if node.is_leaf:
            return 1
        return self._subtree_size(node.left) + self._subtree_size(node.right)
    
    def prove_exclusion(self, value: Any) -> Optional[ExclusionProof]:
        """
        Generate an exclusion proof for a value.
        
        Args:
            value: The value to prove exclusion for
            
        Returns:
            ExclusionProof if value is NOT in tree, None if value IS in tree
        """
        if not self.sorted_values:
            # Empty tree - trivial exclusion proof
            return ExclusionProof(
                target=value,
                predecessor=None,
                successor=None,
                predecessor_proof=None,
                successor_proof=None,
                root_hash=b''
            )
        
        if value in self.sorted_values:
            return None  # Can't prove exclusion for included value
        
        # Find predecessor and successor
        predecessor = None
        successor = None
        
        for v in self.sorted_values:
            if v < value:
                predecessor = v
            elif v > value and successor is None:
                successor = v
                break
        
        # Generate inclusion proofs for predecessor and successor
        predecessor_proof = self.prove_inclusion(predecessor) if predecessor is not None else None
        successor_proof = self.prove_inclusion(successor) if successor is not None else None
        
        return ExclusionProof(
            target=value,
            predecessor=predecessor,
            successor=successor,
            predecessor_proof=predecessor_proof,
            successor_proof=successor_proof,
            root_hash=self.root.hash
        )
    
    def merge_with(self, other: 'ExclusionTLog') -> 'ExclusionTLog':
        """
        Merge this tree with another tree, creating a new combined tree.
        
        This is the "recursive merging" aspect - we can combine transparency logs
        by merging their sorted values and rebuilding.
        
        Args:
            other: Another ExclusionTLog to merge with
            
        Returns:
            New ExclusionTLog containing values from both trees
        """
        combined_values = self.sorted_values + other.sorted_values
        return ExclusionTLog(combined_values)
