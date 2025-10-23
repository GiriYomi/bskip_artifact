import argparse
import json
import logging
import os
import re
import shutil
from typing import Dict, List, Optional, Tuple


logger = logging.getLogger(__name__)


def find_checkpoints_root(path: str) -> str:
    """
    Return the checkpoints root directory for a given OpenEvolve output path.
    - If path itself is a checkpoints directory, return it.
    - If path contains a checkpoints/ subdir, return that.
    - If path is a single checkpoint_X directory, use its parent as checkpoints root.
    """
    abspath = os.path.abspath(path)
    base = os.path.basename(abspath)
    if base == "checkpoints":
        return abspath
    if base.startswith("checkpoint_"):
        return os.path.dirname(abspath)
    candidate = os.path.join(abspath, "checkpoints")
    if os.path.isdir(candidate):
        return candidate
    raise RuntimeError(f"Could not locate 'checkpoints' under {path}")


def list_checkpoint_dirs(checkpoints_root: str) -> List[Tuple[str, int]]:
    """
    List checkpoint directories as (path, iteration) pairs, sorted by iteration ascending.
    Skips 'checkpoint_final' if present.
    """
    entries = []
    for name in os.listdir(checkpoints_root):
        full = os.path.join(checkpoints_root, name)
        if not os.path.isdir(full):
            continue
        if name == "checkpoint_final":
            continue
        if name.startswith("checkpoint_"):
            m = re.match(r"checkpoint_(\d+)", name)
            if not m:
                continue
            it = int(m.group(1))
            entries.append((full, it))
    entries.sort(key=lambda x: x[1])
    return entries


def iter_program_files(checkpoint_dir: str) -> List[str]:
    programs = os.path.join(checkpoint_dir, "programs")
    if not os.path.isdir(programs):
        return []
    return [os.path.join(programs, f) for f in os.listdir(programs) if f.endswith('.json') and os.path.isfile(os.path.join(programs, f))]


def load_program_id(json_path: str) -> Optional[str]:
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        pid = data.get('id')
        if isinstance(pid, str) and pid:
            return pid
        # fallback to filename stem
        return os.path.splitext(os.path.basename(json_path))[0]
    except Exception as e:
        logger.warning(f"Failed to read {json_path}: {e}")
        return None


def collect_unique_programs(checkpoints_root: str, dry_run: bool = False) -> Dict[str, Dict[str, str]]:
    """
    Scan all checkpoints and collect first-seen unique program ids.
    Returns a dict: id -> { 'source': path, 'checkpoint': name, 'iteration': int }
    """
    results: Dict[str, Dict[str, str]] = {}
    seen: set = set()
    checkpoints = list_checkpoint_dirs(checkpoints_root)
    logger.info(f"Found {len(checkpoints)} checkpoints under {checkpoints_root}")
    for cp_path, iteration in checkpoints:
        cp_name = os.path.basename(cp_path)
        files = iter_program_files(cp_path)
        logger.debug(f"Checkpoint {cp_name}: {len(files)} program files")
        for jf in files:
            pid = load_program_id(jf)
            if not pid:
                continue
            if pid in seen:
                continue
            seen.add(pid)
            results[pid] = {
                'source': jf,
                'checkpoint': cp_name,
                'iteration': iteration,
            }
    logger.info(f"Collected {len(results)} unique programs")
    if dry_run:
        for pid, info in list(results.items())[:10]:
            logger.info(f"Sample: id={pid} from {info['checkpoint']} -> {info['source']}")
    return results


def ensure_empty_dir(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def write_manifest(target_dir: str, mapping: Dict[str, Dict[str, str]]) -> None:
    # Write as a sorted list for readability
    items = [
        {
            'id': pid,
            'source': info['source'],
            'checkpoint': info['checkpoint'],
            'iteration': info['iteration'],
        }
        for pid, info in mapping.items()
    ]
    items.sort(key=lambda x: (x['iteration'], x['id']))
    manifest_path = os.path.join(target_dir, 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(items, f, indent=2)
    logger.info(f"Wrote manifest with {len(items)} entries to {manifest_path}")


def copy_unique_programs(checkpoints_root: str, mapping: Dict[str, Dict[str, str]]) -> str:
    final_dir = os.path.join(checkpoints_root, 'checkpoint_final')
    programs_dir = os.path.join(final_dir, 'programs')
    os.makedirs(final_dir, exist_ok=True)
    ensure_empty_dir(programs_dir)
    copied = 0
    for pid, info in mapping.items():
        src = info['source']
        dst = os.path.join(programs_dir, f"{pid}.json")
        shutil.copy2(src, dst)
        copied += 1
    write_manifest(final_dir, mapping)
    logger.info(f"Copied {copied} unique programs into {programs_dir}")
    return final_dir


def write_final_metadata(checkpoints_root: str, final_dir: str, mapping: Dict[str, Dict[str, str]]) -> None:
    programs_dir = os.path.join(final_dir, 'programs')
    # Group program ids by island (from each program's embedded metadata if available)
    islands_map: Dict[int, List[str]] = {}
    for fname in os.listdir(programs_dir):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(programs_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed reading {fpath}: {e}")
            continue
        pid = data.get('id') or os.path.splitext(fname)[0]
        island = None
        # Try multiple locations for island info
        if isinstance(data.get('metadata'), dict):
            island = data['metadata'].get('island', island)
        if island is None and isinstance(data.get('metadata'), dict):
            island = data['metadata'].get('island_index', island)
        if island is None and isinstance(data.get('metadata'), dict):
            island = data['metadata'].get('islandId', island)
        if island is None:
            island = 0
        try:
            island_idx = int(island)
        except Exception:
            island_idx = 0
        islands_map.setdefault(island_idx, []).append(pid)

    # Build islands list; fill gaps with empty lists for stable indexing
    max_idx = max(islands_map.keys()) if islands_map else 0
    islands: List[List[str]] = []
    for i in range(max_idx + 1):
        ids = islands_map.get(i, [])
        ids.sort()
        islands.append(ids)

    # Derive last_iteration as max from mapping
    last_iteration = 0
    if mapping:
        try:
            last_iteration = max(int(info.get('iteration', 0)) for info in mapping.values())
        except Exception:
            last_iteration = 0

    # Try to borrow archive from latest checkpoint metadata if available
    archive: List[str] = []
    try:
        checkpoints = list_checkpoint_dirs(checkpoints_root)
        checkpoints = [c for c in checkpoints if os.path.basename(c[0]) != 'checkpoint_final']
        if checkpoints:
            latest_cp, _ = max(checkpoints, key=lambda x: x[1])
            meta_path = os.path.join(latest_cp, 'metadata.json')
            if os.path.isfile(meta_path):
                with open(meta_path, 'r', encoding='utf-8') as f:
                    latest_meta = json.load(f)
                if isinstance(latest_meta.get('archive'), list):
                    archive = [str(x) for x in latest_meta['archive']]
    except Exception as e:
        logger.debug(f"Unable to import archive from latest checkpoint: {e}")

    out = {
        'islands': islands,
        'archive': archive,
        'last_iteration': last_iteration,
    }
    out_path = os.path.join(final_dir, 'metadata.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f)
    logger.info(f"Wrote metadata.json for checkpoint_final with {len(islands)} islands: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Collect all unique OpenEvolve programs across checkpoints")
    parser.add_argument('--path', 
        default='/Users/girigiri_yomi/Udel_Proj/bskip_artifact/openevolve_output_lock_free', # TODO change this
        help='Path to OpenEvolve run (contains checkpoints/) or the checkpoints/ directory itself')
    parser.add_argument('--dry-run', action='store_true', help='Scan and report without copying files')
    parser.add_argument('--log-level', default='INFO', help='Logging level (DEBUG, INFO, WARNING, ERROR)')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format='[%(levelname)s] %(message)s')

    checkpoints_root = find_checkpoints_root(args.path)
    logger.info(f"Checkpoints root: {checkpoints_root}")

    mapping = collect_unique_programs(checkpoints_root, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("Dry run complete - no files copied")
        return

    final_dir = copy_unique_programs(checkpoints_root, mapping)
    # Ensure metadata.json exists for visualizer
    write_final_metadata(checkpoints_root, final_dir, mapping)
    logger.info(f"Done. Final folder: {final_dir}")


if __name__ == '__main__':
    main()


