import os
import asyncio
from openevolve import OpenEvolve
from openevolve.config import Config, LLMConfig, LLMModelConfig, DatabaseConfig, EvaluatorConfig, PromptConfig


async def main() -> None:
    # Ensure we have an API key in the environment
    if not os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY is not set in the environment')
    
    # Set dataset directory for evaluator
    base_dir = '/home/yomi/0Projects/bskip_artifact'
    os.environ['BSKIP_DATASET_DIR'] = os.path.join(base_dir, 'data/unif_ycsb/uniform')

    # Configure OpenEvolve for the bskiplist C++ optimization task
    config = Config(
        max_iterations=6,
        checkpoint_interval=2,
        diff_based_evolution=True,
        max_code_length=300000,
        llm=LLMConfig(
            api_base='https://api.openai.com/v1',
            api_key=os.environ.get('OPENAI_API_KEY'),
            models=[LLMModelConfig(name='gpt-5-mini', weight=1.0)],
            evaluator_models=[LLMModelConfig(name='gpt-5-mini', weight=1.0)],
            temperature=0.7,
            max_tokens=20000,
            timeout=360,
            retries=4,
            retry_delay=2,
        ),

        prompt=PromptConfig(
            system_message=("""
                You are evolving the entire B-skiplist data structure (bskip.h) to maximize YCSB throughput through revolutionary algorithmic innovations. You have complete freedom to redesign the core algorithms and data organization. Do NOT change public function signatures, class/struct names, or headers included by ycsb.cpp. The binary must compile with the provided Makefile and produce correct map semantics.

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

                Maintain readable, well-structured C++ with clear invariants and comprehensive error checking. Document your innovations clearly.
            """),
        ),

        database=DatabaseConfig(
            db_path=os.path.join(base_dir, 'bskiplist/openevolve_output_fullfile'),
            population_size=75,
            archive_size=30,
            num_islands=4,
            elite_selection_ratio=0.2,
            exploitation_ratio=0.6,
        ),
        evaluator=EvaluatorConfig(
            timeout=600,
            cascade_evaluation=False,
            parallel_evaluations=1,
        ),
    )

    openevolve = OpenEvolve(
        initial_program_path=os.path.join(base_dir, 'bskiplist/bskip.h'),
        evaluation_file=os.path.join(base_dir, 'bskiplist/evaluator.py'),
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


