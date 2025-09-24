import os
import asyncio
from openevolve import OpenEvolve
from openevolve.config import Config, LLMConfig, LLMModelConfig, DatabaseConfig, EvaluatorConfig, PromptConfig


async def main() -> None:
    # Ensure we have an API key in the environment
    if not os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY is not set in the environment')

    # Configure OpenEvolve for the bskiplist C++ optimization task
    config = Config(
        max_iterations=20,
        checkpoint_interval=2,
        diff_based_evolution=True,
        max_code_length=200000,
        llm=LLMConfig(
            api_base='https://api.openai.com/v1',
            api_key=os.environ.get('OPENAI_API_KEY'),
            models=[LLMModelConfig(name='gpt-5', weight=1.0)],
            evaluator_models=[LLMModelConfig(name='gpt-5', weight=1.0)],
            temperature=0.7,
            max_tokens=20000,
            timeout=360,
            retries=4,
            retry_delay=2,
        ),

        prompt=PromptConfig(
            system_message=("""
                You are evolving the insert() function in the B-skiplist (bskip.h lines 869-1679) to maximize YCSB throughput. Focus exclusively on algorithmic improvements to the insert operation. Do NOT change public function signatures, class/struct names, or headers included by ycsb.cpp. The binary must compile with the provided Makefile and produce correct map semantics.

                Primary objective:
                - Maximize median run throughput (ops/us) reported by ycsb by optimizing the insert() function specifically.

                Constraints and correctness:
                - Preserve exact semantics of insert(key,value): successful insertion returns true, duplicate keys update values (for maps), maintain sorted order.
                - Keep thread-safety guarantees: no data races, deadlocks, or undefined behavior under concurrent access.
                - Maintain structural invariants: proper skip list levels, correct node linking, balanced promotion probabilities.
                - Do not introduce external dependencies; rely on C++20 and available intrinsics only.

                Focus areas for insert() optimization (lines 869-1679):
                1. **Node splitting strategy** (lines 1293-1487): Improve split point selection, implement "split-with-spare" to reduce cascade splits, adapt split thresholds based on access patterns.
                2. **Promotion and level assignment** (lines 897-898, 948-965): Optimize coin flipping logic, consider adaptive promotion probabilities based on current structure density.
                3. **Lock management** (lines 975-1046, 1064-1126): Implement lock elision for low-contention scenarios, optimize hand-over-hand locking patterns, reduce lock scope where safe.
                4. **Memory allocation patterns** (lines 909-941): Consider micro-batching node allocations, pre-allocation strategies, or memory pool optimizations.
                5. **Search path optimization** (lines 1051-1133): Improve horizontal traversal efficiency, reduce pointer chasing, add prefetching hints.

                Algorithmic ideas to explore:
                - Biased split policy: split nodes to preserve cache-hot prefixes and minimize future splits under burst insertions
                - Adaptive thresholds: adjust MAX_KEYS utilization based on observed access patterns or contention levels  
                - Lock-free fast paths: use optimistic techniques for common cases (e.g., insert into non-full leaf with no contention)
                - Batched operations: accumulate multiple inserts per thread before applying structural changes
                - Smart promotion: bias coin flips based on current structure imbalance or hotspot detection

                Keep changes cohesive and well-localized within the insert() function. Maintain readable, well-structured C++ with clear invariants and debug assertions.
            """),
        ),

        database=DatabaseConfig(
            db_path='./examples/bskiplist/openevolve_output',
            population_size=50,
            archive_size=20,
            num_islands=3,
            elite_selection_ratio=0.2,
            exploitation_ratio=0.7,
        ),
        evaluator=EvaluatorConfig(
            timeout=300,
            cascade_evaluation=False,
            parallel_evaluations=2,
        ),
    )

    openevolve = OpenEvolve(
        initial_program_path='./bskiplist/bskip.h',
        evaluation_file='./bskiplist/evaluator.py',
        config=config,
    )

    best_program = await openevolve.run()

    if best_program is None:
        print('No best program found.')
        return

    print('Best program metrics:')
    for name, value in best_program.metrics.items():
        if isinstance(value, (int, float)):
            print(f'  {name}: {value:.4f}')
        else:
            print(f'  {name}: {value}')


if __name__ == '__main__':
    asyncio.run(main())


