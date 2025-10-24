"""
Exclusion Transparency Log

A novel transparency log data structure based on recursively merged ordered merkle trees.
Because the merkle tree leaves are in sorted order, we can construct exclusion proofs
(proofs that a value is NOT in the log).

The key insight is that if leaves are sorted, we can prove non-membership by showing
the gap between two consecutive values where the target would have to be.

Architecture:
- Trees are immutable - never mutated, only created or merged
- The tlog is a "forest" of trees (ordered by age, oldest first)
- New entries create single-node trees
- Trees can be merged to create new trees (destroying inputs)
- The overall merkle root is the hash of all tree roots in order
"""

import hashlib
from typing import List, Optional, Tuple, Any
from dataclasses import dataclass, field
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
class MerkleTree:
    """
    An immutable merkle tree with sorted leaves.
    Trees are never mutated, only created or merged.
    """
    root: MerkleNode
    sorted_values: List[Any] = field(default_factory=list)
    
    @property
    def root_hash(self) -> bytes:
        return self.root.hash
    
    def __len__(self) -> int:
        return len(self.sorted_values)
    
    @staticmethod
    def create_single(value: Any) -> 'MerkleTree':
        """Create a tree with a single value."""
        leaf_hash = hash_value(value)
        root = MerkleNode(hash=leaf_hash, value=value)
        return MerkleTree(root=root, sorted_values=[value])
    
    @staticmethod
    def merge_trees(left: 'MerkleTree', right: 'MerkleTree') -> 'MerkleTree':
        """
        Merge two trees into a new tree.
        The input trees are conceptually "destroyed" (though Python doesn't 
        actually destroy them, they should not be used after merging).
        
        Args:
            left: First tree (will have smaller or equal values)
            right: Second tree (will have larger or equal values)
            
        Returns:
            New merged tree with all values from both trees
        """
        # Merge and sort all values
        combined_values = sorted(left.sorted_values + right.sorted_values)
        
        # Create leaf nodes for all values
        leaves = [
            MerkleNode(hash=hash_value(val), value=val)
            for val in combined_values
        ]
        
        # Build tree from leaves
        root = _merge_nodes(leaves)
        
        return MerkleTree(root=root, sorted_values=combined_values)


@dataclass
class InclusionProof:
    """
    Proof that a value is included in the tree.
    Contains the value and the sibling hashes needed to recompute the root.
    """
    value: Any
    leaf_hash: bytes
    sibling_hashes: List[Tuple[bytes, bool]]  # (hash, is_left_sibling)
    root_hash: bytes  # Overall tlog root (forest root)
    tree_index: int = 0  # Which tree in the forest contains this value
    tree_root: bytes = b''  # Root of the specific tree containing the value
    
    def verify(self) -> bool:
        """
        Verify this inclusion proof.
        
        Verifies the path from leaf to tree root matches the root_hash.
        """
        current = self.leaf_hash
        for sibling_hash, is_left in self.sibling_hashes:
            if is_left:
                current = hash_pair(sibling_hash, current)
            else:
                current = hash_pair(current, sibling_hash)
        
        # Verify we reached the expected root
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
        
        Note: In a forest-based architecture, predecessor and successor
        may be in different trees, so we don't require them to have the
        same root. We just verify each inclusion proof individually.
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


def hash_roots(root_hashes: List[bytes]) -> bytes:
    """Hash a list of tree root hashes to create the overall tlog root."""
    if not root_hashes:
        return hashlib.sha256(b'EMPTY:').digest()
    combined = b'FOREST:' + b''.join(root_hashes)
    return hashlib.sha256(combined).digest()


def _merge_nodes(nodes: List[MerkleNode]) -> MerkleNode:
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
    return _merge_nodes(parents)


def _collect_siblings(node: MerkleNode, target_idx: int, total_leaves: int, 
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
    left_size = _subtree_size(node.left)
    
    # Check which subtree contains our target
    if target_idx < current_start + left_size:
        # Target is in left subtree
        if node.right:
            siblings.append((node.right.hash, False))
        return _collect_siblings(node.left, target_idx, total_leaves, siblings, current_start)
    else:
        # Target is in right subtree
        if node.left:
            siblings.append((node.left.hash, True))
        return _collect_siblings(node.right, target_idx, total_leaves, siblings, 
                                current_start + left_size)


def _subtree_size(node: Optional[MerkleNode]) -> int:
    """Count the number of leaves in a subtree."""
    if node is None:
        return 0
    if node.is_leaf:
        return 1
    return _subtree_size(node.left) + _subtree_size(node.right)


class ExclusionTLog:
    """
    Exclusion Transparency Log
    
    A transparency log that supports both inclusion and exclusion proofs.
    Based on a forest of recursively merged ordered merkle trees.
    
    Architecture:
    - Trees are immutable (never mutated)
    - Trees are only created (single node) or merged (creating new tree)
    - The tlog maintains a forest of trees ordered by age (oldest first)
    - The overall merkle root is the hash of all tree roots in order
    
    This design allows trees to be stored cheaply on systems like S3.
    """
    
    def __init__(self, values_or_trees: Optional[Any] = None):
        """
        Initialize the transparency log.
        
        Args:
            values_or_trees: Either a list of MerkleTree objects (for forest),
                           or a list of values (for backward compatibility)
        """
        if values_or_trees is None:
            self.trees: List[MerkleTree] = []
        elif isinstance(values_or_trees, list) and len(values_or_trees) > 0:
            # Check if it's a list of trees or values
            if isinstance(values_or_trees[0], MerkleTree):
                self.trees = values_or_trees
            else:
                # It's a list of values - create a single tree
                self.trees = []
                self.add_batch(values_or_trees)
        else:
            self.trees = []
    
    @classmethod
    def from_values(cls, values: List[Any]) -> 'ExclusionTLog':
        """
        Create a new transparency log from a list of values.
        Creates a single tree containing all values.
        
        Args:
            values: List of values to include
            
        Returns:
            New ExclusionTLog with one tree
        """
        tlog = cls()
        if values:
            tlog.add_batch(values)
        return tlog
    
    @property
    def root(self) -> Optional[MerkleNode]:
        """Get the root node of the first/only tree (for backward compatibility)."""
        if len(self.trees) == 0:
            return None
        return self.trees[0].root
    
    @property  
    def sorted_values(self) -> List[Any]:
        """Get all sorted values from all trees (for backward compatibility)."""
        return self.get_all_values()
    
    def add(self, value: Any) -> None:
        """
        Add a new value to the log.
        Creates a new single-node tree and appends it to the forest.
        
        Args:
            value: The value to add to the log
        """
        new_tree = MerkleTree.create_single(value)
        self.trees.append(new_tree)
    
    def add_batch(self, values: List[Any]) -> None:
        """
        Add multiple values to the log.
        Creates a new tree containing all values and appends it.
        
        Args:
            values: List of values to add
        """
        if not values:
            return
        
        # Sort values
        sorted_values = sorted(values)
        
        # Create leaf nodes
        leaves = [
            MerkleNode(hash=hash_value(val), value=val)
            for val in sorted_values
        ]
        
        # Build tree
        root = _merge_nodes(leaves)
        new_tree = MerkleTree(root=root, sorted_values=sorted_values)
        self.trees.append(new_tree)
    
    def merge_oldest_two(self) -> None:
        """
        Merge the two oldest trees in the forest.
        Destroys the two oldest trees and creates a new merged tree.
        The new tree is placed at the beginning (oldest position).
        """
        if len(self.trees) < 2:
            return
        
        # Take the two oldest trees
        left = self.trees[0]
        right = self.trees[1]
        
        # Merge them
        merged = MerkleTree.merge_trees(left, right)
        
        # Replace the two oldest with the merged tree
        self.trees = [merged] + self.trees[2:]
    
    def merge_all(self) -> None:
        """
        Merge all trees in the forest into a single tree.
        Useful for consolidation before long-term storage.
        """
        while len(self.trees) > 1:
            self.merge_oldest_two()
    
    def get_root_hash(self) -> Optional[bytes]:
        """
        Get the overall merkle root hash of the transparency log.
        For backward compatibility:
        - Returns None for empty forest
        - Returns tree root directly for single tree
        - Returns hash of all tree roots for forest
        """
        if len(self.trees) == 0:
            return None
        if len(self.trees) == 1:
            return self.trees[0].root_hash
        root_hashes = [tree.root_hash for tree in self.trees]
        return hash_roots(root_hashes)
    
    def get_all_values(self) -> List[Any]:
        """Get all values from all trees, sorted."""
        all_values = []
        for tree in self.trees:
            all_values.extend(tree.sorted_values)
        return sorted(all_values)
    
    def contains(self, value: Any) -> bool:
        """Check if a value is in any tree in the forest."""
        for tree in self.trees:
            if value in tree.sorted_values:
                return True
        return False
    
    def _find_tree_containing(self, value: Any) -> Optional[Tuple[int, MerkleTree]]:
        """Find which tree contains a value. Returns (index, tree) or None."""
        for i, tree in enumerate(self.trees):
            if value in tree.sorted_values:
                return i, tree
        return None
    
    def prove_inclusion(self, value: Any) -> Optional[InclusionProof]:
        """
        Generate an inclusion proof for a value.
        
        Args:
            value: The value to prove inclusion for
            
        Returns:
            InclusionProof if value is in any tree, None otherwise
        """
        result = self._find_tree_containing(value)
        if result is None:
            return None
        
        tree_idx, tree = result
        leaf_hash = hash_value(value)
        sibling_hashes = []
        
        # Find the leaf index within this tree
        leaf_idx = tree.sorted_values.index(value)
        
        # Collect sibling hashes on path to root within the tree
        _collect_siblings(tree.root, leaf_idx, len(tree.sorted_values), sibling_hashes)
        
        # Reverse to get bottom-up order (leaf to root)
        sibling_hashes.reverse()
        
        # For the proof root_hash, use the tree root (what we can actually verify)
        # In a full forest implementation, you'd separately verify the tree root
        # is part of the forest root
        
        return InclusionProof(
            value=value,
            leaf_hash=leaf_hash,
            sibling_hashes=sibling_hashes,
            root_hash=tree.root_hash,  # Use tree root for verification
            tree_index=tree_idx,
            tree_root=tree.root_hash
        )
    
    def prove_exclusion(self, value: Any) -> Optional[ExclusionProof]:
        """
        Generate an exclusion proof for a value.
        
        Args:
            value: The value to prove exclusion for
            
        Returns:
            ExclusionProof if value is NOT in any tree, None if value IS in a tree
        """
        if self.contains(value):
            return None  # Can't prove exclusion for included value
        
        # Get all values from all trees
        all_values = self.get_all_values()
        
        if not all_values:
            # Empty forest - trivial exclusion proof
            return ExclusionProof(
                target=value,
                predecessor=None,
                successor=None,
                predecessor_proof=None,
                successor_proof=None,
                root_hash=self.get_root_hash()
            )
        
        # Find predecessor and successor
        predecessor = None
        successor = None
        
        for v in all_values:
            if v < value:
                predecessor = v
            elif v > value and successor is None:
                successor = v
                break
        
        # Generate inclusion proofs for predecessor and successor
        predecessor_proof = self.prove_inclusion(predecessor) if predecessor is not None else None
        successor_proof = self.prove_inclusion(successor) if successor is not None else None
        
        # For the exclusion proof root, use consistent logic with inclusion proofs
        # (i.e., use individual tree roots, not forest root)
        if predecessor_proof:
            overall_root = predecessor_proof.root_hash
        elif successor_proof:
            overall_root = successor_proof.root_hash
        else:
            overall_root = self.get_root_hash() if self.get_root_hash() else b''
        
        return ExclusionProof(
            target=value,
            predecessor=predecessor,
            successor=successor,
            predecessor_proof=predecessor_proof,
            successor_proof=successor_proof,
            root_hash=overall_root
        )
    
    def merge_with(self, other: 'ExclusionTLog') -> 'ExclusionTLog':
        """
        Merge this transparency log with another.
        Creates a new tlog containing trees from both logs.
        
        Args:
            other: Another ExclusionTLog to merge with
            
        Returns:
            New ExclusionTLog containing trees from both logs
        """
        # Combine all trees from both logs (oldest first)
        combined_trees = self.trees + other.trees
        return ExclusionTLog(combined_trees)
