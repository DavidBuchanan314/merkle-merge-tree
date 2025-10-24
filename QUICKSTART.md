# Quick Reference Guide

## Installation

```bash
# Clone the repository
git clone https://github.com/DavidBuchanan314/exclusion-tlog.git
cd exclusion-tlog

# Or install as a package
pip install -e .
```

## Basic Usage

```python
from exclusion_tlog import ExclusionTLog

# Create a transparency log
tlog = ExclusionTLog([10, 20, 30, 40, 50])

# Check if value is in log
assert tlog.contains(30)
assert not tlog.contains(25)

# Get root hash
root = tlog.get_root_hash()
```

## Inclusion Proofs

```python
# Generate proof that 30 IS in the log
proof = tlog.prove_inclusion(30)

# Verify the proof
assert proof.verify()

# Access proof data
print(f"Proving value: {proof.value}")
print(f"Root hash: {proof.root_hash.hex()}")
print(f"Proof size: {len(proof.sibling_hashes)} hashes")
```

## Exclusion Proofs

```python
# Generate proof that 25 is NOT in the log
proof = tlog.prove_exclusion(25)

# Verify the proof
assert proof.verify()

# Access proof data
print(f"Target: {proof.target}")
print(f"Predecessor: {proof.predecessor}")  # 20
print(f"Successor: {proof.successor}")      # 30
```

## Merging Trees

```python
tlog1 = ExclusionTLog([10, 30, 50])
tlog2 = ExclusionTLog([20, 40, 60])

# Merge creates a new combined tree
merged = tlog1.merge_with(tlog2)

assert merged.sorted_values == [10, 20, 30, 40, 50, 60]
```

## Working with Different Data Types

```python
# Integers
int_log = ExclusionTLog([1, 2, 3, 4, 5])

# Strings
str_log = ExclusionTLog(["apple", "banana", "cherry"])

# Custom objects (must be comparable)
from dataclasses import dataclass

@dataclass
class Record:
    id: int
    name: str
    
    def __lt__(self, other):
        return self.id < other.id
    
    def __eq__(self, other):
        return self.id == other.id

records = [
    Record(1, "Alice"),
    Record(2, "Bob"),
    Record(3, "Charlie")
]
record_log = ExclusionTLog(records)
```

## Common Patterns

### Certificate Transparency

```python
# Store issued certificates
certs = ExclusionTLog([
    "cert-alice-2025.pem",
    "cert-bob-2025.pem",
    # ... more certificates
])

# Prove a certificate is logged
proof = certs.prove_inclusion("cert-alice-2025.pem")

# Prove a certificate is NOT logged (potentially fraudulent)
proof = certs.prove_exclusion("cert-eve-2025.pem")
```

### Revocation List

```python
# Track revoked credential IDs
revoked = ExclusionTLog([101, 205, 387, 492])

# Prove a credential is NOT revoked (still valid)
credential_id = 300
proof = revoked.prove_exclusion(credential_id)
if proof and proof.verify():
    print(f"Credential {credential_id} is valid (not revoked)")
```

### Audit Log

```python
# Store event IDs in audit log
audit_log = ExclusionTLog([1001, 1002, 1003, 1004])

# Prove event is logged
proof = audit_log.prove_inclusion(1002)

# Prove suspicious event is NOT logged
proof = audit_log.prove_exclusion(9999)
```

## Performance Characteristics

| Tree Size | Inclusion Proof | Exclusion Proof | Build Time |
|-----------|----------------|-----------------|------------|
| 100       | ~7 hashes      | ~14 hashes      | <1ms       |
| 1,000     | ~10 hashes     | ~20 hashes      | <10ms      |
| 10,000    | ~14 hashes     | ~28 hashes      | <100ms     |
| 100,000   | ~17 hashes     | ~34 hashes      | ~1s        |
| 1,000,000 | ~20 hashes     | ~40 hashes      | ~10s       |

All proof sizes are O(log n) 🎉

## Testing

```bash
# Run all tests
python -m unittest test_exclusion_tlog.py

# Run with verbose output
python -m unittest test_exclusion_tlog.py -v

# Run specific test
python -m unittest test_exclusion_tlog.TestInclusionProofs.test_inclusion_proof_single_value
```

## Examples

```bash
# Run comprehensive examples
python example.py
```

## API Cheat Sheet

```python
# ExclusionTLog methods
tlog = ExclusionTLog(values)        # Create tree
tlog.build(values)                   # Rebuild tree
tlog.get_root_hash()                 # Get root hash
tlog.contains(value)                 # Check membership
tlog.prove_inclusion(value)          # Generate inclusion proof
tlog.prove_exclusion(value)          # Generate exclusion proof
tlog.merge_with(other)               # Merge trees

# InclusionProof methods
proof.verify()                       # Verify proof

# ExclusionProof methods
proof.verify()                       # Verify proof
```

## Tips and Tricks

1. **Pre-sort if possible**: If your data is already sorted, you can skip the sorting step
2. **Batch operations**: Build the tree once with all values rather than adding one at a time
3. **Cache root hash**: Store the root hash for quick verification later
4. **Serialize proofs**: Proofs can be serialized to JSON for transmission
5. **Immutable**: Trees are immutable - merging creates a new tree

## Common Mistakes

❌ **Don't** modify `sorted_values` directly
```python
tlog.sorted_values.append(100)  # Wrong! Tree is now inconsistent
```

✅ **Do** rebuild the tree
```python
new_values = tlog.sorted_values + [100]
tlog = ExclusionTLog(new_values)  # Correct!
```

❌ **Don't** try to prove exclusion for included values
```python
proof = tlog.prove_exclusion(30)  # Returns None if 30 is in tree
```

✅ **Do** check membership first
```python
if tlog.contains(30):
    proof = tlog.prove_inclusion(30)
else:
    proof = tlog.prove_exclusion(30)
```

## Further Reading

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed design and algorithms
- [DIAGRAMS.md](DIAGRAMS.md) - Visual diagrams with examples
- [README.md](README.md) - Full documentation and use cases
