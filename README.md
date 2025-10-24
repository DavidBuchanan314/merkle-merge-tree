# Exclusion Transparency Log

A novel transparency log data structure based on recursively merged ordered merkle trees. Unlike traditional transparency logs that only support inclusion proofs, this implementation also supports **exclusion proofs** - cryptographic proofs that a value is NOT in the log.

## Key Features

- ✅ **Inclusion Proofs**: Prove a value IS in the log
- ✅ **Exclusion Proofs**: Prove a value is NOT in the log (novel feature!)
- ✅ **Sorted Merkle Trees**: Leaves stored in sorted order for efficient searching
- ✅ **Recursive Merging**: Combine multiple transparency logs
- ✅ **Cryptographically Secure**: Based on SHA-256 merkle trees
- ✅ **Logarithmic Proof Size**: O(log n) proof sizes for efficiency

## Installation

No external dependencies required! Just Python 3.7+.

```bash
# Clone the repository
git clone https://github.com/DavidBuchanan314/exclusion-tlog.git
cd exclusion-tlog
```

## Quick Start

```python
from exclusion_tlog import ExclusionTLog

# Create a transparency log with some values
tlog = ExclusionTLog([10, 25, 40, 55, 70, 85])

# Generate an inclusion proof (prove 55 IS in the log)
inclusion_proof = tlog.prove_inclusion(55)
assert inclusion_proof.verify()  # ✓ Proof is valid

# Generate an exclusion proof (prove 50 is NOT in the log)
exclusion_proof = tlog.prove_exclusion(50)
assert exclusion_proof.verify()  # ✓ Proof is valid
print(f"50 falls between {exclusion_proof.predecessor} and {exclusion_proof.successor}")
# Output: 50 falls between 40 and 55
```

## How It Works

### The Innovation: Sorted Merkle Trees

Traditional merkle trees can prove that an item IS in a collection, but cannot prove that an item is NOT in the collection. Our key insight is to **store leaves in sorted order**, which enables exclusion proofs.

```
Tree with values [10, 25, 40, 55, 70, 85]:

                    Root
                   /    \
                  A      B
                 / \    / \
                C   D  E   F
               /|  /| /|  /|
              10 25 40 55 70 85  ← Sorted left to right!
```

### Exclusion Proofs

To prove that `50` is NOT in the tree above, we show:

1. **Predecessor**: 40 is in the tree (with inclusion proof)
2. **Successor**: 55 is in the tree (with inclusion proof)
3. **Gap**: 40 < 50 < 55

Since the tree is sorted and we've proven 40 and 55 are consecutive values, 50 cannot be in the tree!

## API Reference

### ExclusionTLog

Main class for the transparency log.

#### `__init__(values: List[Any] = None)`

Create a new transparency log.

```python
tlog = ExclusionTLog([10, 20, 30, 40, 50])
```

#### `build(values: List[Any]) -> None`

Build or rebuild the tree with new values.

```python
tlog.build([1, 2, 3, 4, 5])
```

#### `get_root_hash() -> bytes`

Get the root hash of the merkle tree.

```python
root = tlog.get_root_hash()
print(root.hex())
```

#### `contains(value: Any) -> bool`

Check if a value is in the log.

```python
if tlog.contains(25):
    print("Value is in the log")
```

#### `prove_inclusion(value: Any) -> InclusionProof`

Generate a cryptographic proof that a value IS in the log.

```python
proof = tlog.prove_inclusion(30)
if proof and proof.verify():
    print("Inclusion proof is valid!")
```

#### `prove_exclusion(value: Any) -> ExclusionProof`

Generate a cryptographic proof that a value is NOT in the log.

```python
proof = tlog.prove_exclusion(35)
if proof and proof.verify():
    print(f"Value {proof.target} is not in the log")
    print(f"It would fall between {proof.predecessor} and {proof.successor}")
```

#### `merge_with(other: ExclusionTLog) -> ExclusionTLog`

Merge this log with another log, creating a new combined log.

```python
tlog1 = ExclusionTLog([10, 30, 50])
tlog2 = ExclusionTLog([20, 40, 60])
merged = tlog1.merge_with(tlog2)
# merged contains: [10, 20, 30, 40, 50, 60]
```

### InclusionProof

Proof that a value is included in the tree.

#### `verify() -> bool`

Verify the inclusion proof.

```python
if proof.verify():
    print("Proof is valid!")
```

**Fields:**
- `value`: The value being proven
- `leaf_hash`: Hash of the leaf node
- `sibling_hashes`: List of (hash, is_left) pairs for verification path
- `root_hash`: Expected root hash

### ExclusionProof

Proof that a value is NOT included in the tree.

#### `verify() -> bool`

Verify the exclusion proof.

```python
if proof.verify():
    print("Value is definitely not in the log!")
```

**Fields:**
- `target`: The value being proven absent
- `predecessor`: Largest value less than target (or None)
- `successor`: Smallest value greater than target (or None)
- `predecessor_proof`: Inclusion proof for predecessor
- `successor_proof`: Inclusion proof for successor
- `root_hash`: Root hash of the tree

## Examples

Run the example script to see the data structure in action:

```bash
python example.py
```

This demonstrates:
- Creating transparency logs
- Generating inclusion and exclusion proofs
- Handling edge cases (empty trees, boundary values)
- Merging multiple logs
- Working with different data types

## Use Cases

### 1. Certificate Transparency

Prove that a certificate either IS or IS NOT in the transparency log.

```python
# Certificate log
certs = ExclusionTLog([
    "cert-alice-2025.pem",
    "cert-bob-2025.pem",
    "cert-charlie-2025.pem"
])

# Prove Alice's cert is logged
proof = certs.prove_inclusion("cert-alice-2025.pem")

# Prove Eve's cert is NOT logged (doesn't exist!)
exclusion = certs.prove_exclusion("cert-eve-2025.pem")
```

### 2. Revocation Lists

Efficiently prove a credential has NOT been revoked.

```python
revoked = ExclusionTLog([101, 205, 387, 492])

# Prove credential 300 is not revoked
proof = revoked.prove_exclusion(300)
if proof.verify():
    print("Credential 300 is valid (not revoked)")
```

### 3. Supply Chain Tracking

Prove goods are tracked or prove no record of counterfeits.

### 4. Audit Logs

Prove specific events are logged or prove absence of unauthorized events.

## Architecture

For detailed information about the data structure, algorithms, and diagrams, see [ARCHITECTURE.md](ARCHITECTURE.md).

Key points:
- **Time Complexity**: O(log n) for proofs, O(n log n) for tree construction
- **Space Complexity**: O(n) for storage, O(log n) for proofs
- **Security**: Based on SHA-256 collision resistance

## Testing

Run the comprehensive test suite:

```bash
python -m unittest test_exclusion_tlog.py -v
```

Tests cover:
- Hash functions and determinism
- Tree construction and sorting
- Inclusion proof generation and verification
- Exclusion proof generation and verification
- Edge cases (empty trees, single values, boundaries)
- Tree merging
- Security properties (tamper resistance)
- Large trees (1000+ values)

## Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| Build tree | O(n log n) | O(n) |
| Inclusion proof | O(log n) | O(log n) |
| Exclusion proof | O(log n) | O(log n) |
| Verify inclusion | O(log n) | O(1) |
| Verify exclusion | O(log n) | O(1) |
| Merge trees | O(n log n) | O(n) |

## How is this different from other transparency logs?

Most transparency logs (like Certificate Transparency) can only prove that an item **is** in the log. They cannot prove that an item is **not** in the log. This is because traditional merkle trees don't have any ordering property.

Our innovation is to **sort the leaves**, which enables:
1. **Exclusion proofs**: Prove non-membership
2. **Efficient searching**: Binary search over sorted values
3. **Gap detection**: Show where a missing value would have to be

The trade-off is that building the tree requires sorting (O(n log n)), but all operations remain logarithmic.

## Contributing

Contributions welcome! This is an experimental project exploring novel transparency log designs.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

David Buchanan

## References

For more on transparency logs and merkle trees:
- [Certificate Transparency (RFC 6962)](https://tools.ietf.org/html/rfc6962)
- [Merkle Trees](https://en.wikipedia.org/wiki/Merkle_tree)
- [Verifiable Data Structures](https://transparency.dev/)
