import os
import sys
import asyncio
from openevolve import OpenEvolve
from openevolve.config import Config, LLMConfig, LLMModelConfig, DatabaseConfig, EvaluatorConfig, PromptConfig
from prompt import prompt1, prompt2, prompt3, prompt4, prompt5, prompt6, prompt7


async def main(prompt_num: int) -> None:
    # Ensure we have an API key in the environment
    if not os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY is not set in the environment')
    
    # Set dataset directory for evaluator
    #base_dir = '/home/yomi/0Projects/bskip_artifact'
    #os.environ['BSKIP_DATASET_DIR'] = os.path.join(base_dir, 'data/unif_ycsb/uniform')


    if os.path.exists('/home/yomi/0Projects/skip_data/uniform/'):
        # Local environment - use full dataset
        base_dir = '/home/yomi/0Projects/bskip_artifact'
        os.environ['BSKIP_DATASET_DIR'] = '/home/yomi/0Projects/skip_data/uniform/'
        print("Running in LOCAL environment (full dataset)")
    else:
        # Cloudlab environment
        base_dir = '/opt/bskip_artifact'
        os.environ['BSKIP_DATASET_DIR'] = '/mydata/skip_data/uniform/'
        print("Running in CLOUDLAB environment")

    # Select prompt based on parameter
    prompts = {1: prompt1, 2: prompt2, 3: prompt3, 4: prompt4, 5: prompt5, 6: prompt6, 7: prompt7}
    if prompt_num not in prompts:
        raise ValueError(f"Invalid prompt number: {prompt_num}. Must be 1, 2, 3, 4, 5, 6, or 7.")
    
    selected_prompt = prompts[prompt_num]
    print(f"Using prompt {prompt_num}")

    # Configure OpenEvolve for the bskiplist C++ optimization task
    config = Config(
        max_iterations=20,
        checkpoint_interval=1,
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
            system_message=selected_prompt,
        ),

        database=DatabaseConfig(
            db_path=os.path.join(base_dir, 'bskiplist/openevolve_output'),
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
    if len(sys.argv) != 2:
        print("Usage: python run_skip.py <prompt_number>")
        print("  prompt_number: 1, 2, 3, 4, 5, 6, or 7")
        sys.exit(1)
    
    try:
        prompt_num = int(sys.argv[1])
        asyncio.run(main(prompt_num))
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


