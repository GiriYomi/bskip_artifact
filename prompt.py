prompt1 = """Optimize the B-skiplist data structure to maximize YCSB throughput. Focus on making the code faster while keeping it simple and correct. Don't change function names or public interfaces. Make sure it compiles and works correctly."""

prompt2 = """You are evolving the entire B-skiplist data structure (bskip.h) to maximize YCSB throughput through revolutionary algorithmic innovations. You have complete freedom to redesign the core algorithms and data organization. Do NOT change public function signatures, class/struct names, or headers included by ycsb.cpp. The binary must compile with the provided Makefile and produce correct map semantics.

                Primary objective:
                - Maximize combined throughput (load + run operations) reported by ycsb through fundamental algorithmic breakthroughs across the entire data structure.

                Constraints and correctness:
                - Preserve exact semantics of all public operations: insert(key,value), value(key), map_range(start,end,fn), map_range_length(start,len,fn).
                - Maintain thread-safety guarantees: no data races, deadlocks, or undefined behavior under concurrent access.
                - Preserve structural correctness: sorted order, range query accuracy, no lost or duplicate keys.
                - Do not introduce external dependencies; rely on C++20 and available intrinsics only.

                Scope for algorithmic revolution (entire file is open for innovation):
                - **Data structure organization**: Reimagine how keys, values, and metadata are stored and accessed
                - **Concurrency paradigms**: Invent new approaches to thread coordination and lock-free algorithms  
                - **Memory management**: Design novel allocation patterns, caching strategies, and data locality optimizations
                - **Search and traversal algorithms**: Create breakthrough approaches to navigation and path optimization
                - **Node management**: Revolutionize splitting, merging, promotion, and structural maintenance
                - **Adaptive behaviors**: Develop algorithms that learn and adapt to workload characteristics

                Your mission is to discover completely novel algorithmic paradigms that fundamentally transform how concurrent data structures operate. Think beyond incremental improvements and explore revolutionary concepts that could redefine the field.

                Core research questions to explore:
                - What if the fundamental assumptions about skiplist organization are wrong?
                - How can machine learning or adaptive principles be embedded directly into the data structure?
                - What novel concurrency models could eliminate traditional bottlenecks?
                - How might the algorithm predict and preemptively optimize for future operations?
                - What unconventional data layouts or access patterns could yield exponential improvements?
                - How can the structure dynamically reorganize itself based on observed patterns?

                Invent new algorithms, don't optimize existing ones. Your goal is to make algorithmic contributions that advance computer science. Be bold, creative, and revolutionary in your approach.

                Maintain readable, well-structured C++ with clear invariants and comprehensive error checking. Document your innovations clearly."""

prompt3 = """You are evolving the entire B-skiplist data structure (bskip.h) to maximize YCSB throughput through revolutionary algorithmic innovations. You have complete freedom to redesign the core algorithms and data organization. Do NOT change public function signatures, class/struct names, or headers included by ycsb.cpp. The binary must compile with the provided Makefile and produce correct map semantics.

Primary objective:
- Maximize combined throughput (load + run operations) reported by ycsb through fundamental algorithmic breakthroughs across the entire data structure.

Constraints and correctness:
- Preserve exact semantics of all public operations: insert(key,value), value(key), map_range(start,end,fn), map_range_length(start,len,fn).
- Maintain thread-safety guarantees: no data races, deadlocks, or undefined behavior under concurrent access.
- Preserve structural correctness: sorted order, range query accuracy, no lost or duplicate keys.
- Do not introduce external dependencies; rely on C++20 and available intrinsics only.

Scope for algorithmic revolution (entire file is open for innovation):
- **Data structure organization**: Reimagine how keys, values, and metadata are stored and accessed
- **Concurrency paradigms**: Invent new approaches to thread coordination and lock-free algorithms  
- **Memory management**: Design novel allocation patterns, caching strategies, and data locality optimizations
- **Search and traversal algorithms**: Create breakthrough approaches to navigation and path optimization
- **Node management**: Revolutionize splitting, merging, promotion, and structural maintenance
- **Adaptive behaviors**: Develop algorithms that learn and adapt to workload characteristics

Your mission is to discover completely novel algorithmic paradigms that fundamentally transform how concurrent data structures operate. Think beyond incremental improvements and explore revolutionary concepts that could redefine the field.

Core research questions to explore:
Practical optimizations
Concurrency/synchronization
Lock-/obstruction-free updates with versioned/tagged pointers; epoch/QSBR or RCU for reads
HTM fast-path with fine-grained lock fallback; optimistic hand-over-hand with validation
Level-wise lock striping with cache-padded spinlocks; flat combining for hot spots
De-dup via elimination/backoff for repeated inserts of the same key
Practical optimizations
Concurrency/synchronization
Lock-/obstruction-free updates with versioned/tagged pointers; epoch/QSBR or RCU for reads
HTM fast-path with fine-grained lock fallback; optimistic hand-over-hand with validation
Level-wise lock striping with cache-padded spinlocks; flat combining for hot spots
De-dup via elimination/backoff for repeated inserts of the same key
Height/structure adaptation
Adaptive p by workload; background top-level rebuild; biased towers for hot keys
Range queries/iteration
Version stamps per node/level for lock-free snapshots; fence pointers as side index
Stable iterators via tombstones + epoch GC (lazy unlink)
Batch/vectorized ops
Batch insert/delete with sorted splices level-by-level; two-finger speculative search
Instrumentation/autotuning
Counters (contention, retries, HTM aborts, heights, cache misses)
Online tuning of p, batch size, reclamation quanta, HTM retries (bandit/hill-climb)
Open research topics
NUMA-optimal, linearizable skiplists with near-linear scalability and lock-free reads
Lock-free range queries at scale with bounded memory and stable iterators
Learned/hybrid indices: RMI-guided top levels with drift handling and P99 analysis
RL/bandit-guided online tuning of p, batching, reclamation, HTM, sharding, NUMA placement
Persistence on NVRAM: fence-minimal, failure-atomic operations compatible with epochs
Formal verification under weak memory (C++11/ARM/RISC-V) with machine-checked proofs
Tail-latency control under hotspots: adaptive heights, mini-indexes, combining with fairness
Energy/efficiency-aware concurrency: sync scheme vs coherence/L3 traffic
Heterogeneous memory/tiering: cold levels on CXL/remote, live migration policies
Security/fault containment: invariants, local repair, self-healing for pointer corruption
Workload-aware shape control: p/level caps for Zipf/monotone/time-series with bounds
Transactional semantics: HTM/STM multi-key ops with graceful fallback

Invent new algorithms, don't optimize existing ones. Your goal is to make algorithmic contributions that advance computer science. Be bold, creative, and revolutionary in your approach.

Maintain readable, well-structured C++ with clear invariants and comprehensive error checking. Document your innovations clearly."""

prompt4 = """

"""


