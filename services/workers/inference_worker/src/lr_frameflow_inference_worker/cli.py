import sys

from lr_edit_serializer import ping as serializer_ping


def main() -> None:
    print(
        "LR-FrameFlow inference worker stub — dequeue, predict, serialize.",
        f"serializer={serializer_ping()}",
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
