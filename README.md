# Merkle Merge Tree (MMT)

> [!CAUTION]
> This is very WIP! All that exists is an incomplete prototype/toy implementation.

The Merkle Merge Tree data structure implements an *authenticated insert-only multiset*. It supports:

- O(logn) insert time
- O(log²n) search time
- O(logn) inclusion proof size
- O(log²n) exclusion proof size
- O(n) size on disk

Superficially it might sound like "Merkle Search Tree, but worse". Although MST enables O(logn) lookups and O(logn) exclusion proofs, the disk access patterns during insertions are chaotic. MMT on the other hand is optmized to use sequential I/O during writes (similar to LSM Trees), enabling higher peak write throughput and greater affinity for static blob storage engines like S3.

Another key advantage of the MMT (over the MST) is that its structure depends only on its cardinality, and its constituent trees are always complete and balanced. On the other hand, malicious (or simply unlucky) MST inputs can unbalance the tree.

It might one day be useful for implementing a Transparency Log for *revocations* of some record type (where a recent exclusion proof demonstrates that the record hasn't been revoked/invalidated yet).

You could also implement a CRDT, leveraging the fact that two (or more!) MMTs can be merged.

Why multiset instead of regular set? It simplifies insert/merge operations. You could implement a regular set but you'd have to check if an element already exists prior to insertion, which would slow things down.

## Logical Structure

Here's a MMT with 12 elements in it.

The overall "Forest" is comprised of two sorted binary merkle trees, one with 8 elements and the other with 4.

The root of the forest is the hash of the concatenated sub-tree roots.

```
                  root
         __________|_________
        |____________________|
          |                |
          O                |
         / \               |
        /   \              |
       /     \             |
      /       \            |
     /         \           |
    O           O          O
   / \         / \        / \
  /   \       /   \      /   \
 O     O     O     O    O     O
/ \   / \   / \   / \  / \   / \
a d   e i   n p   q z  b c   o x
```

An *inclusion* proof for an element is the merkle path back to the root (with the required hashes for a verifier to reconstruct the root hash).

An exclusion proof for the overall MMT is an array of exclusion proofs for each subtree. A subtree exclusion proof is a pair of *inclusion* proofs for the elements on either side of where the missing element *would* be if it existed (except if the missing element would be on the far left or far right of the tree)

The leaf nodes themselves are hashes of the element object.

Let's go back in time to an earlier version of the tree:

```
                root
         ________|________
        |_________________|
          |             |
          O             |
         / \            |
        /   \           |
       /     \          |
      /       \         |
     /         \        |
    O           O       |
   / \         / \      |
  /   \       /   \     |
 O     O     O     O    O
/ \   / \   / \   / \  / \
a d   e i   n p   q z  b o
```

Now let's add the element `c`

```
                root
         ________|______________
        |____________________c__|
          |             |
          O             |
         / \            |
        /   \           |
       /     \          |
      /       \         |
     /         \        |
    O           O       |
   / \         / \      |
  /   \       /   \     |
 O     O     O     O    O
/ \   / \   / \   / \  / \
a d   e i   n p   q z  b o
```

For singular elements, they are special-cased to be stored directly in the list of subtree roots.

Let's add another element, `x`

```
                root
         ________|______________
        |_______________________|
          |             |    |
          O             |    |
         / \            |    |
        /   \           |    |
       /     \          |    |
      /       \         |    |
     /         \        |    |
    O           O       |    |
   / \         / \      |    |
  /   \       /   \     |    |
 O     O     O     O    O    O
/ \   / \   / \   / \  / \  / \
a d   e i   n p   q z  b o  c x
```

Wait!, this tree is not in its canonical form. The rightmost two subtrees can be merged together, producing the final state of the MMT:

```
                  root
         __________|_________
        |____________________|
          |                |
          O                |
         / \               |
        /   \              |
       /     \             |
      /       \            |
     /         \           |
    O           O          O
   / \         / \        / \
  /   \       /   \      /   \
 O     O     O     O    O     O
/ \   / \   / \   / \  / \   / \
a d   e i   n p   q z  b c   o x
```

The tree is canonical now (there are no more mergeable pairs of subtrees)

Note that at all times, the elements in each subtree are in sorted order.

## Disk Layout

Consider this subtree:

```
          d
         / \
        /   \
       /     \
      /       \
     /         \
    b           f
   / \         / \
  /   \       /   \
 a     c     e     g
/ \   / \   / \   / \
1 2   3 4   5 6   7 8
```

Numbers `1-8` represent elements (specifically, hashes of their values), and letters `a-d` represent intermediate hashes (with `d` being the merkle root)

The hashes forming the tree are serialised in the following order:

```
12a34cb56e78gfd
```

This means that merging two trees involves only seqential reads from the "source" trees, and only sequential writes to the "destination" tree.

How the serialised trees are actually stored is an open question. My thought is to give each one a UUID filename and slap it on disk (or maybe sqlite for the smaller trees).

## Deferred Merge

While adding a new element to the MMT is fast on average, every time the tree cardinality rolls over a power of 2, a lot of merge operations happen at once. It may be acceptable to leave the MMT in a not-fully-merged state for some amount of time. Proof sizes will not be minimal, but not far off. Might be some way to formalize this using Gray Code. I haven't figured out the details here yet.
