#!/usr/bin/env python3
"""
Example usage of the Exclusion Transparency Log

This demonstrates how to use the ExclusionTLog for both inclusion and exclusion proofs.
"""

from exclusion_tlog import ExclusionTLog


def print_separator(title=""):
    """Print a visual separator."""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)
    print()


def bytes_to_hex(b: bytes) -> str:
    """Convert bytes to short hex string for display."""
    return b.hex()[:16] + "..."


def main():
    print_separator("Exclusion Transparency Log - Examples")
    
    # Example 1: Create a simple tree
    print("Example 1: Creating a transparency log")
    print("-" * 70)
    
    values = [10, 25, 40, 55, 70, 85]
    print(f"Creating tree with values: {values}")
    
    tlog = ExclusionTLog(values)
    print(f"Tree created with root hash: {bytes_to_hex(tlog.get_root_hash())}")
    print(f"Sorted values in tree: {tlog.sorted_values}")
    
    # Example 2: Inclusion proof
    print_separator("Example 2: Inclusion Proof")
    
    value_to_prove = 55
    print(f"Generating inclusion proof for value: {value_to_prove}")
    
    inclusion_proof = tlog.prove_inclusion(value_to_prove)
    if inclusion_proof:
        print(f"✓ Inclusion proof generated")
        print(f"  Leaf hash: {bytes_to_hex(inclusion_proof.leaf_hash)}")
        print(f"  Number of sibling hashes: {len(inclusion_proof.sibling_hashes)}")
        print(f"  Root hash: {bytes_to_hex(inclusion_proof.root_hash)}")
        
        # Verify the proof
        is_valid = inclusion_proof.verify()
        print(f"\nVerification: {'✓ VALID' if is_valid else '✗ INVALID'}")
    else:
        print("✗ Could not generate inclusion proof (value not in tree)")
    
    # Example 3: Exclusion proof
    print_separator("Example 3: Exclusion Proof")
    
    value_not_in_tree = 50
    print(f"Generating exclusion proof for value: {value_not_in_tree}")
    print(f"(This value is NOT in the tree)")
    
    exclusion_proof = tlog.prove_exclusion(value_not_in_tree)
    if exclusion_proof:
        print(f"✓ Exclusion proof generated")
        print(f"  Target value: {exclusion_proof.target}")
        print(f"  Predecessor: {exclusion_proof.predecessor}")
        print(f"  Successor: {exclusion_proof.successor}")
        print(f"  Gap: {exclusion_proof.predecessor} < {value_not_in_tree} < {exclusion_proof.successor}")
        
        # Verify the proof
        is_valid = exclusion_proof.verify()
        print(f"\nVerification: {'✓ VALID' if is_valid else '✗ INVALID'}")
        
        # Show that both predecessor and successor are proven to be in tree
        if exclusion_proof.predecessor_proof:
            pred_valid = exclusion_proof.predecessor_proof.verify()
            print(f"  Predecessor inclusion proof: {'✓ VALID' if pred_valid else '✗ INVALID'}")
        if exclusion_proof.successor_proof:
            succ_valid = exclusion_proof.successor_proof.verify()
            print(f"  Successor inclusion proof: {'✓ VALID' if succ_valid else '✗ INVALID'}")
    else:
        print("✗ Could not generate exclusion proof (value IS in tree)")
    
    # Example 4: Edge case - value smaller than all entries
    print_separator("Example 4: Exclusion Proof - Edge Case (smaller than all)")
    
    value_too_small = 5
    print(f"Generating exclusion proof for value: {value_too_small}")
    print(f"(This value is smaller than all values in tree)")
    
    exclusion_proof = tlog.prove_exclusion(value_too_small)
    if exclusion_proof:
        print(f"✓ Exclusion proof generated")
        print(f"  Target value: {exclusion_proof.target}")
        print(f"  Predecessor: {exclusion_proof.predecessor}")
        print(f"  Successor: {exclusion_proof.successor}")
        
        is_valid = exclusion_proof.verify()
        print(f"\nVerification: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    # Example 5: Edge case - value larger than all entries
    print_separator("Example 5: Exclusion Proof - Edge Case (larger than all)")
    
    value_too_large = 100
    print(f"Generating exclusion proof for value: {value_too_large}")
    print(f"(This value is larger than all values in tree)")
    
    exclusion_proof = tlog.prove_exclusion(value_too_large)
    if exclusion_proof:
        print(f"✓ Exclusion proof generated")
        print(f"  Target value: {exclusion_proof.target}")
        print(f"  Predecessor: {exclusion_proof.predecessor}")
        print(f"  Successor: {exclusion_proof.successor}")
        
        is_valid = exclusion_proof.verify()
        print(f"\nVerification: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    # Example 6: Merging transparency logs
    print_separator("Example 6: Merging Transparency Logs")
    
    print("Creating two separate transparency logs:")
    tlog1 = ExclusionTLog([10, 30, 50])
    tlog2 = ExclusionTLog([20, 40, 60])
    
    print(f"Tree 1 values: {tlog1.sorted_values}")
    print(f"Tree 1 root: {bytes_to_hex(tlog1.get_root_hash())}")
    print(f"Tree 2 values: {tlog2.sorted_values}")
    print(f"Tree 2 root: {bytes_to_hex(tlog2.get_root_hash())}")
    
    print("\nMerging the two trees...")
    merged = tlog1.merge_with(tlog2)
    
    print(f"Merged tree values: {merged.sorted_values}")
    print(f"Merged tree root: {bytes_to_hex(merged.get_root_hash())}")
    
    # Verify we can prove inclusion for values from both original trees
    print("\nVerifying merged tree contains values from both original trees:")
    for value in [10, 20, 30, 40, 50, 60]:
        proof = merged.prove_inclusion(value)
        is_valid = proof.verify() if proof else False
        print(f"  Value {value}: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    # Example 7: String values
    print_separator("Example 7: Working with String Values")
    
    certificates = [
        "cert-alice-2025.pem",
        "cert-bob-2025.pem",
        "cert-charlie-2025.pem",
        "cert-diana-2025.pem"
    ]
    
    print(f"Creating certificate transparency log with: {certificates}")
    cert_tlog = ExclusionTLog(certificates)
    
    # Prove a certificate is in the log
    print("\nProving cert-bob-2025.pem is in the log:")
    cert_inclusion = cert_tlog.prove_inclusion("cert-bob-2025.pem")
    if cert_inclusion and cert_inclusion.verify():
        print("✓ Certificate is in the log (inclusion proof valid)")
    
    # Prove a certificate is NOT in the log
    print("\nProving cert-eve-2025.pem is NOT in the log:")
    cert_exclusion = cert_tlog.prove_exclusion("cert-eve-2025.pem")
    if cert_exclusion and cert_exclusion.verify():
        print("✓ Certificate is NOT in the log (exclusion proof valid)")
        print(f"  Would fall between: {cert_exclusion.predecessor} and {cert_exclusion.successor}")
    
    # Example 8: Empty tree
    print_separator("Example 8: Empty Tree")
    
    empty_tlog = ExclusionTLog([])
    print("Created empty transparency log")
    print(f"Root hash: {empty_tlog.get_root_hash()}")
    
    exclusion_from_empty = empty_tlog.prove_exclusion(42)
    if exclusion_from_empty:
        print(f"✓ Exclusion proof for value 42 in empty tree")
        print(f"  Predecessor: {exclusion_from_empty.predecessor}")
        print(f"  Successor: {exclusion_from_empty.successor}")
        is_valid = exclusion_from_empty.verify()
        print(f"  Verification: {'✓ VALID' if is_valid else '✗ INVALID'}")
    
    print_separator("Examples Complete")
    print("\nSee ARCHITECTURE.md for detailed documentation on the data structure.")
    print("See README.md for API documentation and use cases.")


if __name__ == "__main__":
    main()
