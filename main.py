r"""

ok. ordered binary tree.

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
import os
import heapq # used for heapq.merge
from typing import Optional, Iterable, BinaryIO
import hashlib

def count_trailing_ones(n: int) -> int:
	return (n ^ (n + 1)).bit_length() - 1

tree_counter = 0 # for testing
class Tree:
	"""
	the minimal tree has height one and contains a single leaf

	trees are immutable

	note: this used to be an in-memory implementation but then I hacked it up to be backed by a
	BinaryIO, which in this instance is files on disk.
	"""

	def __init__(self, data: BinaryIO, height: int) -> None:
		global tree_counter # for testing
		tree_counter += 1 # for testing
		#assert(len(data) % 32 == 0)
		#num_hashes, rem = divmod(len(data), 32)
		#if rem != 0:
		#	raise ValueError("invalid data length (not a multiple of 32 bytes)")
		#self.height = num_hashes.bit_length()
		#if num_hashes == 0 or num_hashes != (2**self.height)-1:
		#	raise ValueError("invalid data length")
		self.height = height
		self.cardinality = 2**(self.height-1)  # number of leaves
		self.data = data
		self.root = self.get_data_entry((2**self.height)-2)#data[-32:]  # XXX: for height=1, "root" will be the leaf value - might wanna think about domain separation

	def __repr__(self) -> str:
		return f"Tree<height={self.height}, root={self.root.hex()}>"

	def __iter__(self):
		"""
		iterate thru leaves
		"""
		self.data.seek(0)
		for i in range(self.cardinality):
			yield self.data.read(32)
			self.data.seek(count_trailing_ones(i) * 32, io.SEEK_CUR)

	def get_data_entry(self, idx) -> bytes:
		self.data.seek(idx*32)
		return self.data.read(32)

	def find_left(self, needle):
		"""
		find the needle, or if not, the item to the left of where the needle would be
		(or the leftmost item, if the needle would be to the left of that)
		"""
		return self._find_inner(needle, [], 0, (2**self.height)-1)

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
		data = open("./trees/tmp", "wb+")#io.BytesIO()
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
		assert(len(stack) == 1)
		os.rename("./trees/tmp", f"./trees/{stack[0].hex()}.bin")
		if self.height > 1:
			os.remove(f"./trees/{self.root.hex()}.bin")
			os.remove(f"./trees/{other.root.hex()}.bin")
		return Tree(data, self.height + 1)

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
		accumulator = Tree(io.BytesIO(entry), 1) # tree of height 1
		i = 1
		while i <= len(self.trees):
			if self.trees[-i].height == accumulator.height:
				accumulator |= self.trees[-i]
			else:
				break
			i += 1
		return Forest(self.trees[:len(self.trees)-(i-1)] + (accumulator,))


if __name__ == "__main__":
	a = Tree(io.BytesIO(b"A"*32), 1)
	b = Tree(io.BytesIO(b"B"*32), 1)
	c = Tree(io.BytesIO(b"C"*32), 1)
	d = Tree(io.BytesIO(b"D"*32), 1)
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


	# benchmark!
	import time
	start = time.time()
	f = Forest()
	NUM_INSERTS = 0x100000
	for i in range(NUM_INSERTS):
		k = i.to_bytes(32)
		f = f.add(k)
	duration = time.time() - start
	print(NUM_INSERTS/duration, "MMT inserts per second") # I get 20K inserts per second on my machine (it was closer to 70K when I was doing everything in-memory)
	print(tree_counter, "total trees")

	"""start = time.time()
	from atmst.blockstore import MemoryBlockStore
	from atmst.mst.node_store import NodeStore
	from atmst.mst.node_wrangler import NodeWrangler
	bs = MemoryBlockStore()
	ns = NodeStore(bs)
	wrangler = NodeWrangler(ns)
	mst = ns.get_node(None).cid
	NUM_INSERTS = 0x10000
	for i in range(NUM_INSERTS):
		mst = wrangler.put_record(mst, str(i), mst)
	duration = time.time() - start
	print(NUM_INSERTS/duration, "MST inserts per second")
	print(len(bs._state), "stored blocks")"""
