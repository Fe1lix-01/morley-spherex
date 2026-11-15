"""
ÉTER CNN prototype: Braai-inspired, NOT SPHEREx-validated.

Requires: numpy, torch.

Use:
    python eter_cnn_mvp.py demo

This generates a synthetic model and sample.

Real inference accepts previously aligned 63x63 cutouts.

Reprojection, PSF matching, valid FLAGS masks and band
matching must be performed before running this CNN.

For real-data training use --dataset <npz> with:
    stamps: (N,3,63,63)
    labels: (N,)

Labels must be verified. Split by sky region or observing
run to avoid data leakage.

The demo uses synthetic stamps ONLY.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


SIZE = 63
SEED = 2601


class MiniBraai(nn.Module):
    """
    Small VGG-style CNN for real/bogus classification.

    Architecture inspired by braai.
    Original braai weights are NOT used.
    """

    def __init__(self) -> None:
        super().__init__()

        self.net = nn.Sequential(
            nn.Conv2d(3, 16, 3, padding=1),
            nn.ReLU(),

            nn.Conv2d(16, 16, 3, padding=1),
            nn.ReLU(),

            nn.MaxPool2d(2),

            nn.Conv2d(16, 32, 3, padding=1),
            nn.ReLU(),

            nn.Conv2d(32, 32, 3, padding=1),
            nn.ReLU(),

            nn.MaxPool2d(2),

            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),

            nn.Linear(32 * 4 * 4, 32),
            nn.ReLU(),

            nn.Dropout(0.2),
            nn.Linear(32, 1),
        )

    def forward(
        self,
        batch: torch.Tensor,
    ) -> torch.Tensor:
        return self.net(batch).squeeze(1)


def normalize_triplet(
    stamp: np.ndarray,
) -> np.ndarray:
    """
    Normalize the three image channels independently.

    Expected shape:
        (3, 63, 63)

    Channel order:
        science
        reference
        difference
    """

    x = np.asarray(stamp, dtype=np.float32)

    if x.shape != (3, SIZE, SIZE):
        raise ValueError(
            f"Expected (3,{SIZE},{SIZE}), got {x.shape}"
        )

    if not np.isfinite(x).all():
        raise ValueError(
            "Non-finite pixels found. "
            "Apply FITS FLAGS/variance masks upstream."
        )

    result = np.empty_like(x)

    for channel in range(3):
        plane = x[channel]

        median = np.median(plane)

        mad = np.median(
            np.abs(plane - median)
        )

        scale = max(
            float(mad) * 1.4826,
            1e-4,
        )

        bounded = np.clip(
            (plane - median) / scale,
            -15.0,
            15.0,
        )

        norm = float(
            np.linalg.norm(bounded)
        )

        result[channel] = (
            bounded
            / max(norm, 1e-6)
            * SIZE
        )

    return result


def make_gaussian(
    y: float,
    x: float,
    sigma: float = 1.5,
) -> np.ndarray:
    """
    Generate a synthetic Gaussian point source.
    """

    yy, xx = np.mgrid[:SIZE, :SIZE]

    return np.exp(
        -0.5
        * (
            (yy - y) ** 2
            + (xx - x) ** 2
        )
        / sigma**2
    ).astype(np.float32)


def synthetic_stamp(
    rng: np.random.Generator,
    label: int,
) -> np.ndarray:
    """
    Generate synthetic images.

    Label 1:
        Moving source or variable source.

    Label 0:
        Noise or instrumental-like artifact.

    This is NOT calibrated SPHEREx data.
    """

    ref = rng.normal(
        0, 0.6, (SIZE, SIZE)
    ).astype(np.float32)

    sci = rng.normal(
        0, 0.6, (SIZE, SIZE)
    ).astype(np.float32)

    # Add stationary background sources.
    for _ in range(
        int(rng.integers(3, 9))
    ):
        y, x = rng.uniform(8, 55, 2)

        flux = float(
            rng.uniform(2, 10)
        )

        psf = make_gaussian(
            y,
            x,
            float(rng.uniform(1.2, 2.0)),
        )

        ref += flux * psf
        sci += flux * psf

    y, x = rng.uniform(18, 45, 2)

    if label == 1:
        # Real-like changes.
        if rng.random() < 0.5:
            # Moving source.
            dy, dx = rng.uniform(
                -4, 4, 2
            )

            if abs(dy) + abs(dx) < 1.5:
                dy += 2.0

            ref += 18 * make_gaussian(
                y, x
            )

            sci += 18 * make_gaussian(
                y + dy,
                x + dx,
            )

        else:
            # Variable source.
            ref += 4 * make_gaussian(
                y, x
            )

            sci += 22 * make_gaussian(
                y, x
            )

    else:
        # Artifact-like changes.
        kind = int(
            rng.integers(0, 3)
        )

        if kind == 0:
            # Hot pixel / cosmic ray.
            sci[int(y), int(x)] += 22

        elif kind == 1:
            # Noise only.
            pass

        else:
            # Readout-like artifact.
            sci[:, int(x)] += float(
                rng.uniform(0.7, 1.7)
            )

    difference = sci - ref

    return np.stack([
        sci,
        ref,
        difference,
    ])


def synth_dataset(
    n: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a balanced synthetic training dataset.
    """

    rng = np.random.default_rng(seed)

    labels = np.tile(
        np.array(
            [0, 1],
            dtype=np.float32,
        ),
        (n + 1) // 2,
    )[:n]

    rng.shuffle(labels)

    stamps = np.stack([
        normalize_triplet(
            synthetic_stamp(rng, int(y))
        )
        for y in labels
    ])

    return (
        stamps.astype(np.float32),
        labels,
    )


def load_training(
    path: Path | None,
    n: int,
) -> tuple[np.ndarray, np.ndarray, str]:
    """
    Load labeled data or generate synthetic examples.
    """

    if path is None:
        stamps, labels = synth_dataset(
            n,
            SEED,
        )

        return (
            stamps,
            labels,
            "synthetic_only",
        )

    with np.load(
        path,
        allow_pickle=False,
    ) as raw:
        stamps = raw["stamps"].astype(
            np.float32
        )

        labels = raw["labels"].astype(
            np.float32
        )

    if (
        stamps.ndim != 4
        or stamps.shape[1:] != (
            3,
            SIZE,
            SIZE,
        )
    ):
        raise ValueError(
            "Training stamps must have shape "
            "(N,3,63,63)"
        )

    if len(stamps) < 10:
        raise ValueError(
            "Need at least 10 labeled stamps"
        )

    if (
        labels.shape != (len(stamps),)
        or not np.isin(
            labels, [0, 1]
        ).all()
    ):
        raise ValueError(
            "Labels must be binary 0/1 "
            "of length N"
        )

    stamps = np.stack([
        normalize_triplet(stamp)
        for stamp in stamps
    ])

    return (
        stamps,
        labels,
        "user_supplied_labeled_stamps",
    )


def train(
    args: argparse.Namespace,
) -> None:
    """
    Train the experimental CNN.
    """

    torch.manual_seed(SEED)

    torch.set_num_threads(
        min(
            torch.get_num_threads(),
            4,
        )
    )

    stamps, labels, source = load_training(
        args.dataset,
        args.examples,
    )

    # Prototype split.
    # Not valid for scientific evaluation if
    # observations or sky fields overlap.
    rng = np.random.default_rng(
        SEED + 1
    )

    indices = rng.permutation(
        len(stamps)
    )

    split = max(
        1,
        int(len(indices) * 0.8),
    )

    train_ids = indices[:split]
    val_ids = indices[split:]

    if len(val_ids) == 0:
        raise ValueError(
            "Need at least 2 examples"
        )

    dataset = TensorDataset(
        torch.from_numpy(
            stamps[train_ids]
        ),
        torch.from_numpy(
            labels[train_ids]
        ),
    )

    loader = DataLoader(
        dataset,
        batch_size=32,
        shuffle=True,
    )

    model = MiniBraai()

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=0.002,
    )

    criterion = nn.BCEWithLogitsLoss()

    for epoch in range(args.epochs):
        model.train()

        running = 0.0

        for x, y in loader:
            optimizer.zero_grad()

            logits = model(x)

            loss = criterion(
                logits,
                y,
            )

            loss.backward()
            optimizer.step()

            running += (
                loss.detach().item()
                * len(y)
            )

        model.eval()

        with torch.no_grad():
            val_x = torch.from_numpy(
                stamps[val_ids]
            )

            predictions = (
                torch.sigmoid(
                    model(val_x)
                ).numpy() >= 0.5
            ).astype(np.int32)

        accuracy = (
            predictions
            == labels[val_ids]
        ).mean()

        print(
            f"epoch {epoch + 1}/{args.epochs}"
            f" | loss={running / len(train_ids):.4f}"
            f" | demo_val_acc={accuracy:.3f}"
        )

    args.out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint = {
        "state_dict": model.state_dict(),
        "source": source,
        "stamp_size": SIZE,
        "architecture": (
            "eter_mini_vgg6_style_v1"
        ),
    }

    torch.save(
        checkpoint,
        args.out,
    )

    print(
        json.dumps(
            {
                "saved": str(args.out),
                "trained_on": source,
                "scientific_validation": False,
            },
            ensure_ascii=False,
        )
    )


def read_inference_stamp(
    path: Path,
) -> np.ndarray:
    """
    Read an aligned three-channel NPZ file.
    """

    with np.load(
        path,
        allow_pickle=False,
    ) as data:
        files = set(data.files)

        if {
            "science",
            "reference",
            "difference",
        }.issubset(files):

            stamp = np.stack([
                data["science"],
                data["reference"],
                data["difference"],
            ])

        elif "stamp" in files:
            stamp = data["stamp"]

        else:
            raise ValueError(
                "Need science, reference, "
                "difference arrays or stamp array"
            )

    return normalize_triplet(
        stamp
    )


def infer(
    args: argparse.Namespace,
) -> None:
    """
    Run inference on a 63x63 image triplet.
    """

    checkpoint = torch.load(
        args.weights,
        map_location="cpu",
        weights_only=True,
    )

    model = MiniBraai()

    model.load_state_dict(
        checkpoint["state_dict"]
    )

    model.eval()

    stamp = read_inference_stamp(
        args.input
    )

    tensor = torch.from_numpy(
        stamp
    )[None]

    with torch.no_grad():
        logits = model(tensor)

        score = float(
            torch.sigmoid(
                logits
            )[0]
        )

    result = {
        "model": (
            "eter_mini_vgg6_style_v1"
        ),
        "score_real_like": round(
            score,
            6,
        ),
        "trained_on": checkpoint["source"],
        "scientifically_validated": False,
        "note": (
            "Experimental CNN score. "
            "NOT a probability of "
            "astrophysical reality."
        ),
    }

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    commands = parser.add_subparsers(
        dest="action",
        required=True,
    )

    # Synthetic demonstration.
    demo = commands.add_parser(
        "demo",
        help=(
            "Train on SYNTHETIC data "
            "and predict one sample"
        ),
    )

    demo.add_argument(
        "--dataset",
        type=Path,
        default=None,
    )

    demo.add_argument(
        "--out",
        type=Path,
        default=Path(
            "eter_cnn_demo.pt"
        ),
    )

    demo.add_argument(
        "--examples",
        type=int,
        default=320,
    )

    demo.add_argument(
        "--epochs",
        type=int,
        default=4,
    )

    # Training.
    trainer = commands.add_parser(
        "train",
        help=(
            "Train from labeled NPZ "
            "or synthetic fallback"
        ),
    )

    trainer.add_argument(
        "--dataset",
        type=Path,
    )

    trainer.add_argument(
        "--out",
        type=Path,
        default=Path(
            "eter_cnn_demo.pt"
        ),
    )

    trainer.add_argument(
        "--examples",
        type=int,
        default=320,
    )

    trainer.add_argument(
        "--epochs",
        type=int,
        default=4,
    )

    # Inference.
    predictor = commands.add_parser(
        "infer",
        help=(
            "Classify aligned NPZ triplet"
        ),
    )

    predictor.add_argument(
        "--input",
        type=Path,
        required=True,
    )

    predictor.add_argument(
        "--weights",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    if args.action == "demo":
        train(args)

        rng = np.random.default_rng(
            SEED + 9
        )

        example = synthetic_stamp(
            rng,
            1,
        )

        sample = args.out.with_suffix(
            ".example.npz"
        )

        np.savez_compressed(
            sample,
            science=example[0],
            reference=example[1],
            difference=example[2],
        )

        print(
            json.dumps({
                "synthetic_example": str(sample)
            })
        )

        infer(
            argparse.Namespace(
                input=sample,
                weights=args.out,
            )
        )

    elif args.action == "train":
        train(args)

    elif args.action == "infer":
        infer(args)


if __name__ == "__main__":
    main()
