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

prompt4 = """You are evolving the B-skiplist's core insert and find algorithms to achieve breakthrough performance through novel algorithmic innovations. Focus exclusively on the fundamental search and insertion logic within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

Primary objective:
- Revolutionize the insert() and find() algorithms to maximize YCSB throughput through fundamental algorithmic breakthroughs in search and insertion strategies.

Core algorithmic challenges to solve:

1. **Search Algorithm Revolution**:
   - Invent new traversal strategies that minimize comparisons and cache misses
   - Design adaptive search paths that learn from access patterns
   - Create novel approaches to level selection and node navigation
   - Explore predictive search techniques that anticipate likely access patterns

2. **Insertion Algorithm Innovation**:
   - Redesign promotion strategies beyond simple coin flipping
   - Invent new node splitting and merging algorithms
   - Create adaptive insertion patterns that optimize for workload characteristics
   - Design novel approaches to maintaining structural invariants

3. **Key Research Directions**:
   - **Adaptive Height Management**: Instead of random promotion, design algorithms that dynamically adjust node heights based on access frequency, key distribution, or workload patterns
   - **Predictive Path Optimization**: Create search algorithms that use historical access patterns to predict optimal traversal paths
   - **Intelligent Node Splitting**: Design splitting strategies that consider key distribution, access patterns, and future growth to minimize future search costs
   - **Cache-Conscious Algorithms**: Invent data layouts and access patterns that maximize cache efficiency and minimize memory bandwidth
   - **Workload-Aware Adaptation**: Create algorithms that automatically adapt their behavior based on observed operation patterns (insert-heavy vs search-heavy workloads)

4. **Algorithmic Innovation Areas**:
   - Replace linear/binary search within nodes with novel search algorithms
   - Design new approaches to level traversal that reduce the number of nodes visited
   - Invent adaptive promotion strategies that optimize for specific workload characteristics
   - Create novel node organization schemes that improve search efficiency
   - Design algorithms that learn and adapt to access patterns over time

Constraints:
- Preserve exact function signatures: insert(traits::element_type k) and find(traits::key_type k)
- Maintain thread-safety and correctness guarantees
- Keep the same public interface and compilation requirements
- Focus only on algorithmic improvements, not code optimization (caching, early stops, etc.)

Your mission is to discover fundamentally new ways of thinking about search and insertion in skiplist-like structures. Think beyond traditional approaches and explore revolutionary concepts that could redefine how these operations work.

Key questions to explore:
- What if search paths could be learned and optimized dynamically?
- How could insertion strategies adapt to minimize future search costs?
- What novel approaches to node organization could eliminate traditional bottlenecks?
- How might the algorithm predict and preemptively optimize for likely access patterns?
- What unconventional traversal strategies could yield exponential improvements?

Invent new algorithms that advance the state of the art in concurrent search structures. Be bold, creative, and revolutionary in your approach to these fundamental operations."""


prompt5 = """You are evolving ONLY the insert() function of the B-skiplist to achieve breakthrough performance through algorithmic innovation. Focus exclusively on the insert() function within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

CRITICAL CONSTRAINT: Implement ONLY ONE creative algorithmic novelty per evolution. Do NOT combine multiple optimization ideas. Choose ONE innovative approach and explore it deeply.

Primary objective:
- Revolutionize the insert() algorithm through ONE fundamental algorithmic breakthrough that maximizes YCSB throughput.

Your mission is to discover ONE fundamentally new way of thinking about insertion in skiplist structures. Think beyond traditional approaches and explore revolutionary concepts that could redefine how insertion works.

Algorithmic Innovation Guidelines:
- Focus on FUNDAMENTAL algorithmic changes, not code optimizations
- NO caching, early stops, or micro-optimizations  
- NO combining multiple ideas - pick ONE and explore it deeply
- Think about the mathematical and algorithmic foundations
- Consider how the innovation changes the fundamental behavior of insertion
- Design for scalability and adaptability

Constraints:
- Preserve exact function signature: insert(traits::element_type k)
- Maintain thread-safety and correctness guarantees
- Keep the same public interface and compilation requirements
- Focus ONLY on the insert() function within EVOLVE-BLOCK markers
- Implement ONE innovative idea per evolution, not multiple optimizations

Be bold, creative, and revolutionary in your approach. The goal is to make a single, significant algorithmic contribution that advances the state of the art in insertion algorithms."""

prompt6 = """You are evolving ONLY the find() function of the B-skiplist to achieve breakthrough performance through algorithmic innovation. Focus exclusively on the find() function within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

CRITICAL CONSTRAINT: Implement ONLY ONE creative algorithmic novelty per evolution. Do NOT combine multiple optimization ideas. Choose ONE innovative approach and explore it deeply.

Primary objective:
- Revolutionize the find() algorithm through ONE fundamental algorithmic breakthrough that maximizes YCSB throughput.

Your mission is to discover ONE fundamentally new way of thinking about search in skiplist structures. Think beyond traditional approaches and explore revolutionary concepts that could redefine how search works.

Algorithmic Innovation Guidelines:
- Focus on FUNDAMENTAL algorithmic changes, not code optimizations
- NO caching, early stops, or micro-optimizations  
- NO combining multiple ideas - pick ONE and explore it deeply
- Think about the mathematical and algorithmic foundations
- Consider how the innovation changes the fundamental behavior of search
- Design for scalability and adaptability

Constraints:
- Preserve exact function signature: find(traits::key_type k)
- Maintain thread-safety and correctness guarantees
- Keep the same public interface and compilation requirements
- Focus ONLY on the find() function within EVOLVE-BLOCK markers
- Implement ONE innovative idea per evolution, not multiple optimizations

Be bold, creative, and revolutionary in your approach. The goal is to make a single, significant algorithmic contribution that advances the state of the art in search algorithms."""

prompt_heuristics = """You are evolving the flip_coins function in the B-skiplist to discover optimal heuristic parameters and decision formulas that maximize YCSB throughput. Focus on the code within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

CRITICAL CONSTRAINT: Implement ONLY ONE algorithmic or heuristic innovation per evolution. Do NOT combine multiple ideas. Choose ONE approach and explore it deeply.

Primary objective:
- Revolutionize the flip_coins function through ONE focused innovation that maximizes YCSB throughput.

Your mission is to discover ONE optimal approach to height selection in skiplist structures. Think beyond current implementations and explore novel concepts.

Innovation Guidelines:
- Think mathematically about optimal height selection strategies
- Explore the relationship between node heights and performance
- Consider both deterministic and probabilistic approaches
- Question assumptions - what if the current approach is fundamentally suboptimal?
- Think about workload characteristics and adaptation
- Explore mathematical functions and their properties

Constraints:
- Preserve the function signature: uint32_t flip_coins(K k)
- Maintain thread-safety and correctness guarantees
- Keep the same public interface and compilation requirements
- Focus ONLY on the flip_coins function within EVOLVE-BLOCK markers
- Implement ONE innovation per evolution

Be bold, creative, and revolutionary in your approach. The goal is to discover fundamentally better ways to select node heights in skiplist structures."""

