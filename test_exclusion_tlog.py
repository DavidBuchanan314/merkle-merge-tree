"""
Tests for Exclusion Transparency Log

Comprehensive test suite for the ExclusionTLog data structure.
"""

import unittest
from exclusion_tlog import (
    ExclusionTLog, 
    InclusionProof, 
    ExclusionProof,
    hash_value,
    hash_pair
)


class TestHashFunctions(unittest.TestCase):
    """Test the hash functions."""
    
    def test_hash_value_deterministic(self):
        """Hash function should be deterministic."""
        value = "test"
        hash1 = hash_value(value)
        hash2 = hash_value(value)
        self.assertEqual(hash1, hash2)
    
    def test_hash_value_different_inputs(self):
        """Different inputs should produce different hashes."""
        hash1 = hash_value("test1")
        hash2 = hash_value("test2")
        self.assertNotEqual(hash1, hash2)
    
    def test_hash_pair_deterministic(self):
        """Hash pair function should be deterministic."""
        left = b"left"
        right = b"right"
        hash1 = hash_pair(left, right)
        hash2 = hash_pair(left, right)
        self.assertEqual(hash1, hash2)
    
    def test_hash_pair_order_matters(self):
        """Hash pair should be order-sensitive."""
        left = b"left"
        right = b"right"
        hash1 = hash_pair(left, right)
        hash2 = hash_pair(right, left)
        self.assertNotEqual(hash1, hash2)


class TestExclusionTLog(unittest.TestCase):
    """Test the ExclusionTLog class."""
    
    def test_empty_tree(self):
        """Test creating an empty tree."""
        tlog = ExclusionTLog([])
        self.assertIsNone(tlog.root)
        self.assertEqual(len(tlog.sorted_values), 0)
        self.assertIsNone(tlog.get_root_hash())
    
    def test_single_value(self):
        """Test tree with single value."""
        tlog = ExclusionTLog([42])
        self.assertIsNotNone(tlog.root)
        self.assertEqual(len(tlog.sorted_values), 1)
        self.assertEqual(tlog.sorted_values[0], 42)
        self.assertIsNotNone(tlog.get_root_hash())
    
    def test_sorted_values(self):
        """Values should be sorted in the tree."""
        values = [50, 10, 30, 20, 40]
        tlog = ExclusionTLog(values)
        self.assertEqual(tlog.sorted_values, [10, 20, 30, 40, 50])
    
    def test_contains(self):
        """Test contains method."""
        tlog = ExclusionTLog([10, 20, 30])
        self.assertTrue(tlog.contains(10))
        self.assertTrue(tlog.contains(20))
        self.assertTrue(tlog.contains(30))
        self.assertFalse(tlog.contains(15))
        self.assertFalse(tlog.contains(40))
    
    def test_duplicate_values(self):
        """Test tree with duplicate values."""
        values = [10, 20, 20, 30]
        tlog = ExclusionTLog(values)
        # After sorting, duplicates should be preserved
        self.assertEqual(tlog.sorted_values, [10, 20, 20, 30])
    
    def test_different_types(self):
        """Test tree with different value types."""
        # Strings
        tlog_str = ExclusionTLog(["banana", "apple", "cherry"])
        self.assertEqual(tlog_str.sorted_values, ["apple", "banana", "cherry"])
        
        # Mixed numeric types
        tlog_num = ExclusionTLog([1, 2.5, 3])
        self.assertTrue(1 in tlog_num.sorted_values)


class TestInclusionProofs(unittest.TestCase):
    """Test inclusion proof generation and verification."""
    
    def test_inclusion_proof_single_value(self):
        """Test inclusion proof for tree with single value."""
        tlog = ExclusionTLog([42])
        proof = tlog.prove_inclusion(42)
        self.assertIsNotNone(proof)
        self.assertEqual(proof.value, 42)
        self.assertTrue(proof.verify())
    
    def test_inclusion_proof_multiple_values(self):
        """Test inclusion proofs for multiple values."""
        values = [10, 20, 30, 40, 50]
        tlog = ExclusionTLog(values)
        
        for value in values:
            proof = tlog.prove_inclusion(value)
            self.assertIsNotNone(proof)
            self.assertEqual(proof.value, value)
            self.assertTrue(proof.verify())
    
    def test_inclusion_proof_not_in_tree(self):
        """Test inclusion proof for value not in tree."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_inclusion(25)
        self.assertIsNone(proof)
    
    def test_inclusion_proof_root_hash(self):
        """Test that inclusion proof has correct root hash."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_inclusion(20)
        self.assertEqual(proof.root_hash, tlog.get_root_hash())
    
    def test_inclusion_proof_sibling_count(self):
        """Test that sibling count is logarithmic."""
        # With 8 values, tree height should be 3, so 3 siblings
        values = list(range(1, 9))
        tlog = ExclusionTLog(values)
        proof = tlog.prove_inclusion(5)
        self.assertIsNotNone(proof)
        # Height should be log2(8) = 3
        self.assertLessEqual(len(proof.sibling_hashes), 3)


class TestExclusionProofs(unittest.TestCase):
    """Test exclusion proof generation and verification."""
    
    def test_exclusion_proof_empty_tree(self):
        """Test exclusion proof for empty tree."""
        tlog = ExclusionTLog([])
        proof = tlog.prove_exclusion(42)
        self.assertIsNotNone(proof)
        self.assertEqual(proof.target, 42)
        self.assertIsNone(proof.predecessor)
        self.assertIsNone(proof.successor)
        self.assertTrue(proof.verify())
    
    def test_exclusion_proof_value_in_tree(self):
        """Test exclusion proof for value that IS in tree."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_exclusion(20)
        self.assertIsNone(proof)  # Can't prove exclusion for included value
    
    def test_exclusion_proof_gap(self):
        """Test exclusion proof for value in gap."""
        tlog = ExclusionTLog([10, 20, 30, 40, 50])
        proof = tlog.prove_exclusion(25)
        
        self.assertIsNotNone(proof)
        self.assertEqual(proof.target, 25)
        self.assertEqual(proof.predecessor, 20)
        self.assertEqual(proof.successor, 30)
        self.assertTrue(proof.verify())
    
    def test_exclusion_proof_smaller_than_all(self):
        """Test exclusion proof for value smaller than all entries."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_exclusion(5)
        
        self.assertIsNotNone(proof)
        self.assertEqual(proof.target, 5)
        self.assertIsNone(proof.predecessor)
        self.assertEqual(proof.successor, 10)
        self.assertTrue(proof.verify())
    
    def test_exclusion_proof_larger_than_all(self):
        """Test exclusion proof for value larger than all entries."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_exclusion(40)
        
        self.assertIsNotNone(proof)
        self.assertEqual(proof.target, 40)
        self.assertEqual(proof.predecessor, 30)
        self.assertIsNone(proof.successor)
        self.assertTrue(proof.verify())
    
    def test_exclusion_proof_predecessor_inclusion(self):
        """Test that predecessor inclusion proof is valid."""
        tlog = ExclusionTLog([10, 20, 30, 40])
        proof = tlog.prove_exclusion(25)
        
        self.assertIsNotNone(proof.predecessor_proof)
        self.assertTrue(proof.predecessor_proof.verify())
    
    def test_exclusion_proof_successor_inclusion(self):
        """Test that successor inclusion proof is valid."""
        tlog = ExclusionTLog([10, 20, 30, 40])
        proof = tlog.prove_exclusion(25)
        
        self.assertIsNotNone(proof.successor_proof)
        self.assertTrue(proof.successor_proof.verify())
    
    def test_exclusion_proof_strings(self):
        """Test exclusion proof with string values."""
        tlog = ExclusionTLog(["apple", "banana", "cherry"])
        proof = tlog.prove_exclusion("avocado")
        
        self.assertIsNotNone(proof)
        self.assertEqual(proof.predecessor, "apple")
        self.assertEqual(proof.successor, "banana")
        self.assertTrue(proof.verify())


class TestTreeMerging(unittest.TestCase):
    """Test merging of transparency logs."""
    
    def test_merge_two_trees(self):
        """Test merging two trees."""
        tlog1 = ExclusionTLog([10, 30, 50])
        tlog2 = ExclusionTLog([20, 40, 60])
        
        merged = tlog1.merge_with(tlog2)
        
        self.assertEqual(merged.sorted_values, [10, 20, 30, 40, 50, 60])
        self.assertIsNotNone(merged.get_root_hash())
    
    def test_merge_empty_tree(self):
        """Test merging with empty tree."""
        tlog1 = ExclusionTLog([10, 20, 30])
        tlog2 = ExclusionTLog([])
        
        merged = tlog1.merge_with(tlog2)
        
        self.assertEqual(merged.sorted_values, [10, 20, 30])
    
    def test_merge_preserves_values(self):
        """Test that merged tree contains all values from both trees."""
        tlog1 = ExclusionTLog([10, 30, 50])
        tlog2 = ExclusionTLog([20, 40, 60])
        
        merged = tlog1.merge_with(tlog2)
        
        for value in [10, 20, 30, 40, 50, 60]:
            self.assertTrue(merged.contains(value))
    
    def test_merge_proofs_valid(self):
        """Test that proofs are valid after merging."""
        tlog1 = ExclusionTLog([10, 30, 50])
        tlog2 = ExclusionTLog([20, 40, 60])
        
        merged = tlog1.merge_with(tlog2)
        
        # Test inclusion proofs
        for value in [10, 20, 30, 40, 50, 60]:
            proof = merged.prove_inclusion(value)
            self.assertIsNotNone(proof)
            self.assertTrue(proof.verify())
        
        # Test exclusion proof
        exclusion = merged.prove_exclusion(25)
        self.assertIsNotNone(exclusion)
        self.assertTrue(exclusion.verify())


class TestProofSecurity(unittest.TestCase):
    """Test security properties of proofs."""
    
    def test_tampered_inclusion_proof_fails(self):
        """Test that tampered inclusion proof fails verification."""
        tlog = ExclusionTLog([10, 20, 30, 40, 50])
        proof = tlog.prove_inclusion(30)
        
        # Tamper with the leaf hash
        proof.leaf_hash = hash_value(31)
        self.assertFalse(proof.verify())
    
    def test_wrong_root_fails(self):
        """Test that proof with wrong root hash fails."""
        tlog = ExclusionTLog([10, 20, 30])
        proof = tlog.prove_inclusion(20)
        
        # Change root hash
        proof.root_hash = b"wrong_hash"
        self.assertFalse(proof.verify())
    
    def test_exclusion_proof_ordering(self):
        """Test that exclusion proof enforces ordering."""
        tlog = ExclusionTLog([10, 20, 30, 40])
        proof = tlog.prove_exclusion(25)
        
        # Verify original proof
        self.assertTrue(proof.verify())
        
        # Swap predecessor and successor (breaks ordering)
        proof.predecessor, proof.successor = proof.successor, proof.predecessor
        proof.predecessor_proof, proof.successor_proof = proof.successor_proof, proof.predecessor_proof
        self.assertFalse(proof.verify())


class TestLargeTree(unittest.TestCase):
    """Test with larger trees."""
    
    def test_large_tree_creation(self):
        """Test creating a tree with many values."""
        values = list(range(1000))
        tlog = ExclusionTLog(values)
        
        self.assertEqual(len(tlog.sorted_values), 1000)
        self.assertIsNotNone(tlog.get_root_hash())
    
    def test_large_tree_inclusion_proofs(self):
        """Test inclusion proofs in large tree."""
        values = list(range(1000))
        tlog = ExclusionTLog(values)
        
        # Test a few random values
        for value in [0, 100, 500, 999]:
            proof = tlog.prove_inclusion(value)
            self.assertIsNotNone(proof)
            self.assertTrue(proof.verify())
            # Proof size should be logarithmic
            self.assertLessEqual(len(proof.sibling_hashes), 10)  # log2(1000) ≈ 10
    
    def test_large_tree_exclusion_proofs(self):
        """Test exclusion proofs in large tree."""
        values = list(range(0, 1000, 2))  # Even numbers only
        tlog = ExclusionTLog(values)
        
        # Test odd numbers (not in tree)
        for value in [1, 101, 501, 999]:
            proof = tlog.prove_exclusion(value)
            self.assertIsNotNone(proof)
            self.assertTrue(proof.verify())


if __name__ == '__main__':
    unittest.main()
