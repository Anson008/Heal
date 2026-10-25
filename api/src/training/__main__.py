"""Train health outcome models and write their bundles.

uv run python -m training                   # all six
uv run python -m training --metric MHLTH    # just one
"""

import argparse
import time
from pathlib import Path

import artifacts

from . import dataset, pipeline

DEFAULT_OUTPUT = Path(__file__).resolve().parents[2] / "models"


def parse(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="training", description="Train health outcome models."
    )
    parser.add_argument(
        "--metric",
        action="append",
        choices=dataset.METRICS,
        help="outcome to train; repeatable, defaults to all of them",
    )
    parser.add_argument("--data", type=Path, default=dataset.DEFAULT_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=0)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse(argv)
    metrics = args.metric or dataset.METRICS
    frame = dataset.load(args.data)

    for metric in metrics:
        print(f"{metric:9s} training on {len(frame)} tracts ...", flush=True)
        started = time.time()

        result = pipeline.run(metric, frame=frame, seed=args.seed)
        directory = artifacts.save(result.bundle(), args.out / metric)

        scores = result.scores
        print(
            f"{metric:9s} forest R2 {scores['test_r2_forest']:.3f}"
            f" -> kriged {scores['test_r2']:.3f}"
            f"   {time.time() - started:.0f}s   {directory}",
            flush=True,
        )
        # The line above scores a model handed the true socio-demographics, which
        # a request never supplies. This one is what the API will actually do.
        print(
            f"{'':9s} served R2 {scores['test_r2_served']:.3f}"
            f"   RMSE {scores['test_rmse_served']:.3f}"
            "   <- the configuration the service runs in, with the eight"
            " unknown predictors imputed",
            flush=True,
        )


if __name__ == "__main__":
    main()
