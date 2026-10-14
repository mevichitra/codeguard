"""``python -m research.finding_identity transform``: the controlled experiment.

Kept apart from :mod:`cli` and free of heavy imports, so ``replay`` and ``summarize``
work without the experiment's extra dependencies (``requirements.txt``).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
MODEL_ENV = "FINDING_IDENTITY_AI_MODEL"
KEY_ENV = "ANTHROPIC_API_KEY"


def add_parser(sub: Any) -> None:
    tp = sub.add_parser(
        "transform",
        help="apply controlled transformations and score every scheme (invariance matrix)",
    )
    tp.add_argument("source", help="local directory, local repository or git URL to clone")
    tp.add_argument("--ref", help="branch or tag to clone (URLs only)")
    tp.add_argument(
        "--transforms",
        default="all",
        help="comma-separated transformations, or 'all' (ai_refactor only with a model)",
    )
    tp.add_argument("--samples", type=int, default=200, help="files with findings to use")
    tp.add_argument("--seed", type=int, default=0, help="seed for sampling files and targets")
    tp.add_argument("--label", help="name for the results (default: directory name)")
    tp.add_argument("--out", type=Path, help="results directory")
    tp.add_argument("--workdir", type=Path, default=HERE / ".repos", help="where to clone")
    tp.add_argument(
        "--categories",
        default="security,performance,quality",
        help="comma-separated rule categories to run",
    )
    tp.add_argument(
        "--reformat-line-length", type=int, default=79, help="line length for 'reformat'"
    )
    tp.add_argument("--heatmap", action="store_true", help="also draw matrix.png (matplotlib)")
    ai = tp.add_argument_group("ai_refactor")
    ai.add_argument("--ai-model", help=f"model name (default: ${MODEL_ENV})")
    ai.add_argument("--ai-api-key", help=f"API key (default: ${KEY_ENV})")
    ai.add_argument(
        "--ai-cache", type=Path, default=HERE / ".cache" / "ai", help="cached model responses"
    )
    ai.add_argument(
        "--ai-offline", action="store_true", help="use cached responses only; never call the API"
    )


def run(args: argparse.Namespace) -> None:
    from .experiment import run_experiment
    from .gitrepo import GitRepo
    from .scan import Scanner, rule_ids_for
    from .schemes import ALL_SCHEMES
    from .transforms import ALL_TRANSFORMS, AIRefactor, Transform, deterministic_transforms

    model = args.ai_model or os.environ.get(MODEL_ENV)
    wanted = [t.strip() for t in args.transforms.split(",") if t.strip()]
    if wanted == ["all"]:
        wanted = [t for t in ALL_TRANSFORMS if t != "ai_refactor" or model]
    unknown = sorted(set(wanted) - set(ALL_TRANSFORMS))
    if unknown:
        raise SystemExit(f"unknown transformations: {', '.join(unknown)}")
    available: dict[str, Transform] = dict(deterministic_transforms(args.reformat_line_length))
    if "ai_refactor" in wanted:
        if not model:
            raise SystemExit(f"ai_refactor needs --ai-model or ${MODEL_ENV}")
        available["ai_refactor"] = AIRefactor(
            model,
            args.ai_cache,
            api_key=args.ai_api_key or os.environ.get(KEY_ENV),
            offline=args.ai_offline,
        )
    transforms = {name: available[name] for name in wanted}

    meta: dict[str, Any] = {"source": args.source, "ai_model": model if model else None}
    local = Path(args.source)
    if local.is_dir():
        root = local
    else:
        repo = GitRepo.open_or_clone(args.source, args.workdir, depth=1, ref=args.ref)
        root = repo.path
        meta["head"] = repo.resolve("HEAD")
        repo.close()
    label = args.label or root.resolve().name
    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    run_experiment(
        root,
        label=label,
        transforms=transforms,
        scanner=Scanner(rule_ids_for(categories), ALL_SCHEMES),
        schemes=ALL_SCHEMES,
        samples=args.samples,
        seed=args.seed,
        out_dir=args.out or HERE / "results" / f"transform-{label}",
        meta={**meta, "categories": categories},
        draw_heatmap=args.heatmap,
    )
