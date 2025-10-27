r"""

ok. ordered binary tree.

when traversing the tree from the top, you need to know which fork to follow. how do we encode this?



          4
         / \
        /   \
       /     \
      /       \
     /         \
    2           6  <- "rightmost value of the left subtree"
   / \         / \
  /   \       /   \
 1     3     5     7
/ \   / \   / \   / \
1 2   3 4   5 6   7 8


Alternatively, you could binary-search the leaves (they are stored linearly - could use regular DB index to accelerate)

If you know a leaf's index, you can immediately know its path.


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

storage order:
12a34cb56e78gfd
(this order means a tree-merge operation uses sequential IO)

(length = 15) = 2^4-1

inclusion proof of "3" would be: 4,a,f
*ex*clusion proof of "3.5" would be inclusion proof of both 3 and 4


A "Forest" is a tuple of trees, ordered from tallest to shortest.
You can add a tree to the forest. If the two trees on the end of the list would be the same size, they are merged.
Repeat until no more merges are possible. (A forest is only considered valid if it is in "minimal" form, per this process - I may relax this to reduce latency, with deferred merges)

The root of the Forest is the hash of the concatenated tree roots.

An inclusion proof for a Forest is an inclusion proof for one of its constituent trees, plus the other hashes you need to compute the root hash.

An *exclusion* proof for a forest is a tuple of exclusion proofs for each tree.


The log is a sequence of Forest roots.

It would be expensive to check if a new entry was already in the tree, so we implement a "multiset" rather than a classic set - i.e. the same item can be added more than once. But inclusion proofs stop after the first found match.





space:

the complete forest, at any given time, occupies O(n) space
inclusion proofs are O(logn)
exclusion proofs are  O((logn)^2) aka O(log²n)  (each tree's proof is O(logn) and there are O(logn) trees (worst case))

the forest tree-list size is O(logn)
a complete log of all forest tree-lists ever would be O(nlogn)
so if we had a billion entries, that's 1TiB of log - but only 32GB of "active" trees.
I thiiiiiink storing dead trees is also O(nlogn)

"""

import io
import heapq # used for heapq.merge
from typing import Optional, Iterable
import hashlib

def count_trailing_ones(n: int) -> int:
	return (n ^ (n + 1)).bit_length() - 1

class Tree:
	"""
	the minimal tree has height one and contains a single leaf

	trees are immutable
	"""

	def __init__(self, data: bytes) -> None:
		assert(len(data) % 32 == 0)
		num_hashes, rem = divmod(len(data), 32)
		if rem != 0:
			raise ValueError("invalid data length (not a multiple of 32 bytes)")
		self.height = num_hashes.bit_length()
		if num_hashes == 0 or num_hashes != (2**self.height)-1:
			raise ValueError("invalid data length")
		self.cardinality = 2**(self.height-1)  # number of leaves
		self.data = data
		self.root = data[-32:]  # XXX: for height=1, "root" will be the leaf value - might wanna think about domain separation

	def __repr__(self) -> str:
		return f"Tree<height={self.height}, root={self.root.hex()}>"

	def __iter__(self):
		"""
		iterate thru leaves
		"""
		offset = 0
		for i in range(self.cardinality):
			yield self.data[offset:offset+32]
			offset += 32 + count_trailing_ones(i) * 32 # skip non-leaf entries

	def get_data_entry(self, idx) -> bytes:
		return self.data[idx*32:idx*32+32]

	def find_left(self, needle):
		"""
		find the needle, or if not, the item to the left of where the needle would be
		(or the leftmost item, if the needle would be to the left of that)
		"""
		return self._find_inner(needle, [], 0, len(t0.data) // 32)

	def _find_inner(self, needle, proof, start, end):
		"""
		binary search to find the data offset
		"""
		mid = start + (end - start) // 2  # this Just Works (!!!)
		mid_data = self.get_data_entry(mid)

		print(mid_data, start, mid, end)

		if end - start == 1:
			return mid_data, proof
	
		if needle < mid_data:
			return self._find_inner(needle, proof + [(0, self.get_data_entry(end - 2))], start, mid)
		else:
			return self._find_inner(needle, proof + [(1, self.get_data_entry(mid - 1))], mid, end - 1)

	def merge(self, other) -> "Tree":
		"""
		merge two trees of equal height n to produce a new tree of height n+1
		"""
		if not isinstance(other, Tree):
			raise TypeError("can only merge subtrees")
		if self.height != other.height:
			raise ValueError("can only merge trees of the same height")
		data = io.BytesIO()
		stack = []
		for i, entry in enumerate(heapq.merge(self, other)):
			data.write(entry)
			stack.append(entry)
			for _ in range(count_trailing_ones(i)):
				# pull two, hash them, emit and push
				b, a = stack.pop(), stack.pop()
				h = hashlib.sha256(a+b).digest()
				data.write(h)
				stack.append(h)
		return Tree(data.getvalue())

	def __or__(self, other) -> "Tree":
		return self.merge(other)


class Forest:
	"""
	forests are immutable.
	"add" operation produces a new forest with the new entry added.
	"""
	cardinality: int
	trees: tuple[Tree, ...]
	root: bytes

	def __init__(self, trees: Optional[Iterable[Tree]]=None) -> None:
		self.trees = () if trees is None else tuple(trees)
		h = hashlib.sha256()
		prev_height = float("Inf")
		cardinality = 0
		for tree in self.trees:
			if tree.height >= prev_height:
				raise ValueError("non-canonical tree order")
			h.update(tree.root)
			prev_height = tree.height
			cardinality += tree.cardinality
		self.root = h.digest()
		self.cardinality = cardinality

	def __repr__(self) -> str:
		return f"Forest<cardinality={self.cardinality}, root={self.root.hex()}, trees={self.trees}>"

	def get_roots(self) -> Iterable:
		raise NotImplementedError("TODO")

	def add(self, entry: bytes) -> "Forest":
		if len(entry) != 32:
			raise ValueError("entry must be 32 bytes long (expects sha256 hash output)")
		accumulator = Tree(entry) # tree of height 1
		i = 1
		while i <= len(self.trees):
			if self.trees[-i].height == accumulator.height:
				accumulator |= self.trees[-i]
			else:
				break
			i += 1
		return Forest(self.trees[:len(self.trees)-(i-1)] + (accumulator,))


if __name__ == "__main__":
	a = Tree(b"A"*32)
	b = Tree(b"B"*32)
	c = Tree(b"C"*32)
	d = Tree(b"D"*32)
	x = a|b
	y = c|d
	z = x|y
	print(list(enumerate(z)))
	print(z.cardinality)
	forest = Forest((z,))
	print(forest.cardinality, forest.root.hex())

	forest = forest.add(b"E"*32)
	print(forest.trees)
	forest = forest.add(b"F"*32)
	print(forest.trees)
	forest = forest.add(b"G"*32)
	print(forest.trees)
	forest = forest.add(b"H"*32)
	print(forest)

	t0 = forest.trees[0]
	print(t0.data)
	
	needle, proof = t0.find_left(b"0"*31 + b"0")
	print(needle, proof)
	#exit()
	accumulator = needle
	for bit, h in proof[::-1]:
		if bit:
			accumulator = hashlib.sha256(h + accumulator).digest()
		else:
			accumulator = hashlib.sha256(accumulator + h).digest()
	print(accumulator.hex())
	assert(accumulator == t0.root)
