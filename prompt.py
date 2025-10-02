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
- What if the fundamental assumptions about skiplist organization are wrong?
- How can machine learning or adaptive principles be embedded directly into the data structure?
- What novel concurrency models could eliminate traditional bottlenecks?
- How might the algorithm predict and preemptively optimize for future operations?
- What unconventional data layouts or access patterns could yield exponential improvements?
- How can the structure dynamically reorganize itself based on observed patterns?
- What if we completely reimagine the skip list as a hybrid structure with multiple specialized components?
- How can we leverage modern CPU features (SIMD, prefetching, branch prediction) in fundamentally new ways?
- What if the data structure could morph between different organizational patterns based on access patterns?
- How can we eliminate the traditional trade-offs between read and write performance?
- What novel memory hierarchy optimizations could provide orders of magnitude improvements?
- How can we design algorithms that are inherently cache-oblivious and NUMA-aware?
- What if we could predict future access patterns and pre-structure the data accordingly?
- How can we eliminate contention points through novel distributed coordination mechanisms?
- What unconventional data representations could provide better compression and faster access?
- How can we design self-tuning algorithms that automatically optimize their parameters?
- What if we could eliminate the need for traditional locking through novel synchronization primitives?
- How can we leverage modern compiler optimizations and hardware features in unexpected ways?
- What if the data structure could learn from its usage patterns and evolve its internal organization?
- How can we design algorithms that are inherently parallel and scale linearly with core count?

Invent new algorithms, don't optimize existing ones. Your goal is to make algorithmic contributions that advance computer science. Be bold, creative, and revolutionary in your approach.

Maintain readable, well-structured C++ with clear invariants and comprehensive error checking. Document your innovations clearly."""
