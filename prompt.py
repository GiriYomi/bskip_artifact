prompt0 = """optimize it"""

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

prompt4 = """You are evolving the B-skiplist's core insert and find algorithms to achieve breakthrough performance through novel algorithmic innovations. 
Focus exclusively on the fundamental search and insertion logic within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

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

Your mission is to discover fundamentally new ways of thinking about search and insertion in skiplist-like structures. 
Think beyond traditional approaches and explore revolutionary concepts that could redefine how these operations work.

Key questions to explore:
- What if search paths could be learned and optimized dynamically?
- How could insertion strategies adapt to minimize future search costs?
- What novel approaches to node organization could eliminate traditional bottlenecks?
- How might the algorithm predict and preemptively optimize for likely access patterns?
- What unconventional traversal strategies could yield exponential improvements?

Invent new algorithms that advance the state of the art in concurrent search structures. Be bold, creative, and revolutionary in your approach to these fundamental operations."""


prompt5 = """You are evolving ONLY the insert() function of the B-skiplist to achieve breakthrough performance through algorithmic innovation. 
Focus exclusively on the insert() function within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

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

prompt7 = """You are evolving the flip_coins function in the B-skiplist to discover optimal heuristic parameters and decision formulas that maximize YCSB throughput. 
Focus on the code within the EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers in bskip.h.

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

# prompt8 is the main prompt for the evolution of the B-skiplist concurrent data structure optimization.
prompt8 = """# B-Skiplist Concurrent Data Structure Optimization

## THE PROBLEM
You are optimizing a concurrent B-skiplist data structure implementation (bskip.h) to maximize throughput on the YCSB benchmark workload. The B-skiplist is a hybrid structure combining skiplist multi-level indexing with B-tree-like node consolidation for improved cache locality.

**Current Performance Context:**
- The baseline implementation already provides correct concurrent map semantics
- The primary bottleneck is runtime performance under high-concurrency YCSB workloads
- Target workload: mixed insert/lookup operations with uniform key distribution
- Execution environment: Multi-core x86-64 with C++20 standard library

**Your Goal:** Discover algorithmic innovations that fundamentally improve throughput while maintaining correctness.

## EVALUATION CRITERIA

**Primary Optimization Goal:**
- Maximize combined throughput: (load phase operations/sec) + (run phase operations/sec)
- Reported by YCSB benchmark after compilation and execution

**Correctness Constraints (Non-Negotiable):**
1. **Semantic Correctness:**
   - insert(key, value): Must insert key-value pairs maintaining sorted order
   - value(key): Must return the correct value for existing keys
   - map_range(start, end, fn): Must apply fn to all keys in [start, end) in sorted order
   - map_range_length(start, len, fn): Must apply fn to len consecutive keys starting from start

2. **Concurrency Safety:**
   - No data races, deadlocks, or undefined behavior under concurrent access
   - Thread-safe operations without corrupting data structure state
   - Linearizable semantics for all operations

3. **Structural Invariants:**
   - Maintain sorted order across all nodes and levels
   - No duplicate keys, no lost insertions
   - Range queries must be accurate and complete

4. **Compilation Requirements:**
   - Must compile with provided Makefile without errors
   - No external dependencies beyond C++20 standard library
   - Preserve all public function signatures and class/struct names

**Performance Metrics:**
- Solutions are ranked by total throughput (higher is better)
- Compilation failures or correctness violations result in zero score
- Focus on algorithmic improvements, not just micro-optimizations

## CONTEXT AND APIS

**Available C++ Features:**
- C++20 standard library (std::atomic, std::memory_order, etc.)
- Compiler intrinsics for lock-free operations (__atomic_*, __builtin_*)
- Standard synchronization primitives (spinlocks, mutexes if needed)
- SIMD intrinsics for x86-64 (if beneficial)

**Code Structure:**
- Evolve code within EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers
- DO NOT change: public function signatures, class/struct names, included headers
- You have complete freedom within evolution blocks to redesign algorithms

**Data Structure Overview:**
- Multi-level skiplist with B-tree-style nodes containing multiple keys
- Nodes use array-based storage for cache efficiency
- Lock-free or fine-grained locking for concurrent access
- Probabilistic height assignment for level promotion

## ALGORITHMIC INNOVATION DIRECTIONS

**Focus Areas for Breakthrough Improvements:**

1. **Concurrency Paradigms:**
   - Lock-free/wait-free algorithms using CAS and versioned pointers
   - Optimistic concurrency with validation
   - Read-copy-update (RCU) or epoch-based memory reclamation
   - Fine-grained locking with reduced contention
   - Flat combining or elimination for hot spots

2. **Search and Traversal:**
   - Adaptive search paths that minimize node visits
   - Predictive prefetching based on access patterns
   - Novel level-skipping strategies
   - Cache-conscious traversal algorithms

3. **Node Management:**
   - Adaptive node splitting/merging based on workload
   - Workload-aware height selection (beyond random coin flips)
   - Dynamic structure reorganization for hot keys
   - Memory layout optimization for cache efficiency

4. **Workload Adaptation:**
   - Learn from access patterns to optimize structure
   - Adaptive parameters (promotion probability, node sizes)
   - Runtime tuning based on contention metrics
   - Specialized fast paths for common cases

**Innovation Philosophy:**
- Seek fundamental algorithmic breakthroughs, not incremental tweaks
- Question core assumptions about skiplist design
- Explore unconventional approaches that could redefine the field
- Balance novelty with practical performance gains

**Guidance on Hints:**
- Start with clean algorithmic innovations without over-constraining the approach
- If stuck, consider: adaptive structures, workload-aware algorithms, novel concurrency patterns
- Avoid combining too many ideas at once - focus on one core innovation per iteration
- Think about what makes the current approach suboptimal for YCSB workloads

## IMPLEMENTATION GUIDELINES

1. **Code Quality:**
   - Write clear, well-structured C++ with descriptive variable names
   - Document algorithmic innovations with concise comments
   - Maintain clear invariants and add assertions where appropriate
   - Avoid overly complex code that obscures the core algorithm

2. **Abstraction Level:**
   - Focus on algorithmic design, not micro-optimizations
   - Avoid relying on external libraries for algorithmic shortcuts
   - Expose algorithmic innovation rather than just using library primitives
   - Balance between novel algorithms and practical implementation

3. **Evolution Strategy:**
   - Implement ONE core algorithmic innovation per iteration
   - Build incrementally on successful approaches
   - Be willing to explore radically different paradigms
   - Document the algorithmic insight behind each change

**Success Criteria:** Deliver a solution that demonstrates measurable throughput improvement through novel algorithmic contributions while maintaining perfect correctness under concurrent execution.
"""


# prompt9 is the main prompt for the evolution of the B-skiplist into a lock-free data structure.
# should be use on full file evolve
prompt9 = """# Lock-Free B-Skiplist Evolution

## THE PROBLEM
Transform the current concurrent B-skiplist implementation (bskip.h) into a lock-free data structure while maximizing YCSB throughput. Replace all blocking locks on the hot paths with non-blocking algorithms that provide linearizable semantics. Do NOT change public function signatures, class/struct names, or headers included by ycsb.cpp. The binary must compile with the provided Makefile and produce correct map semantics.

## EVALUATION CRITERIA

**Primary Optimization Goal:**
- Maximize total YCSB throughput: (load ops/sec) + (run ops/sec)

**Correctness Constraints (Non-Negotiable):**
1. Semantic correctness:
   - insert(key, value): inserts key-value preserving sorted order; no duplicates
   - value(key): returns correct value for existing key; unspecified for missing
   - map_range(start, end, fn): applies fn to all keys in [start, end) in sorted order
   - map_range_length(start, len, fn): applies fn to len consecutive keys starting at start
2. Concurrency safety:
   - Linearizable semantics for all public operations
   - Lock-free progress for insert(), value(), exists(); range APIs must be non-blocking (lock-free preferred; obstruction-free or validated-snapshot acceptable)
   - No data races or undefined behavior
3. Structural invariants:
   - Global sorted order within and across nodes/levels
   - No lost updates, no duplicate keys
   - Next pointers and next_header remain consistent and monotonic
4. Compilation requirements:
   - Compile with provided Makefile
   - No external dependencies beyond C++20
   - Preserve all public function signatures and class/struct names

## CONTEXT AND APIS
- Evolve code only within EVOLVE-BLOCK-START and EVOLVE-BLOCK-END markers when present; otherwise keep scope minimal and localized
- Environment: C++20 on x86-64; std::atomic, fences, and intrinsics available
- Current code uses per-node locks; your mission is to eliminate blocking locks from hot paths

## LOCK-FREE REQUIREMENTS
1. Progress guarantees:
   - insert(), value(), exists(): lock-free (system-wide progress guaranteed)
   - map_range(), map_range_length(): non-blocking; either lock-free or obstruction-free with validation/snapshot semantics
2. Linearization points:
   - Writes: the successful CAS that links a new node/leaf or publishes a new immutable leaf version
   - Reads: the moment a validated version/tag is observed for the path/leaf being read
3. Memory reclamation (mandatory):
   - Implement safe reclamation without external libs: epoch-based reclamation (QSBR/EBR) or hazard pointers; include minimal implementation in this file if needed
   - Prevent ABA via version/tag bits on pointers or sequence counters
4. Atomicity and ordering:
   - Use std::atomic for all shared pointers/headers; publish with release; read with acquire; use CAS with strong ordering at link/install points

## DESIGN DIRECTIONS (HINTS, NOT REQUIREMENTS)
- Readers: optimistic traversal with version validation (per-node version/tag). If a change is detected, restart from the highest verified level
- Writers: copy-on-write for leaves (build new leaf image, then publish pointer via CAS); for internal splits, install right sibling first, then publish separator key bottom-up (help-along if in-progress is observed)
- Use versioned/tagged pointers to encode small state bits (e.g., IN_PROGRESS, DELETED)
- Child and next pointers are atomic; next_header maintained atomically and validated against child headers
- Range queries: validated snapshot using per-node version stamps; retry on version change, or traverse immutable leaf images created by concurrent writers

## PROHIBITED
- Blocking mutexes, reader-writer locks, condition variables on hot paths
- External GC/RCU libraries or kernel primitives
- Changing public APIs, includes, or Makefile flags

## IMPLEMENTATION GUIDELINES
- Keep code readable; document invariants, linearization points, and helping rules
- Assert ordering invariants (sorted keys; next < next->next; header monotonicity)
- Minimize CAS width by decomposing multi-step updates into publishable single-word installs with helping where needed
- Favor cache-friendly immutable leaf images for writers; readers validate versions without copying

## SUCCESS CRITERIA
- Compiles with the provided Makefile
- Maintains perfect correctness under stress (no corruption, no deadlocks)
- Demonstrably higher YCSB throughput than the baseline with locks
"""


prompt10 = """"""



"""
A clear and well-scoped problem formulation is the foundation of effective algorithm evolution.
Provide structured specifications. Many execution and algorithm failures trace back to missing
context, such as critical details about the problem or absent code API documentation. A welldesigned prompt should be as specific and structured as possible, clearly defining three key areas:
• The problem: what is the core task to solve.
• The evaluation criteria: how a solution will be evaluated, including optimization goals and
correctness constraints.
• The context: any necessary information, such as required APIs.
We recommend drafting prompts with external LLMs (e.g., ChatGPT, Gemini, etc.) to craft a structure before launching evolution.
Provide a suitable base program. The choice of base program strongly shapes the trajectory of
algorithm evolution. Buggy or weak baselines waste iterations on trivial fixes (budget exhaustion),
while a strong, clean baseline can accelerate progress toward meaningful improvements. For example, in the LLM-SQL case study, the published baseline already achieved near state-of-the-art prefix
hit rate; the main bottleneck was runtime, so ∼100 iterations sufficed to evolve a solution that was
3× faster without loss in PHR.
Conversely, overly strong baselines that encode near-SOTA solutions or rely on high-level APIs
can limit the search to shallow micro-optimizations. In the Can’t-be-Late problem (Section 5.1.1),
evolution from a simple greedy baseline produced better results than starting from the stronger
Uniform Progress policy, which restricted exploration. We recommend seeding evolution with clean,
minimal, high-quality baselines, e.g., using coding assistants such as Claude Code.
Provide suitable solution hints. While a detailed problem specification is always beneficial, the
value of providing solution hints – specific suggestions for how the system should approach the
problem – is more nuanced. Too much guidance can risk premature convergence and prevent the
discovery of novel solutions, while too little can make the search inefficient (i.e., stuck-in-the-loop).
For example, in the EPLB problem, hints could have prevented wasted iterations on “extreme”
replication strategies. However, in the transaction scheduling use case, hints about batching biased
the search toward sub-optimal designs, whereas leaving it unconstrained led to a 30% faster greedy
policy in OpenEvolve.
We find that providing intermediate human feedback as hints is especially effective when the search
gets stuck in the loop. In summary, we recommend trying several prompts with different levels of
hint specificity and inject relevant hints as how the evolution progresses.
Choose a suitable level of abstraction. We recommend exposing only the level of abstraction that
matches your goal. Allowing full access to high-level external library APIs can sometimes lead
to sub-optimal optimizations: e.g., trivial speedups from replacing custom operators with PyTorch
primitives, while blocking deeper innovation. To encourage algorithmic advances, restrict API access to help the system explore new strategies rather than rely on pre-built solutions. On the other
hand, when the goal is execution efficiency, providing optimized library access is appropriate. In
practice, tuning this boundary between enabling useful shortcuts and enforcing genuine problemsolving is critical to avoid micro-optimizations.
"""