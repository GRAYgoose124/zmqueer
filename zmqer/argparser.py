import argparse
from random import randint


def argparser():
    parser = argparse.ArgumentParser()
    # logging
    parser.add_argument(
        "-lt",
        "--log-to",
        type=str,
        default="stdout",
        choices=["stdout", "file", None],
        help="Where to log output.",
    )
    parser.add_argument(
        "-v",
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "v"],
        help="Logging level",
    )
    parser.add_argument(
        "-la",
        "--log-all",
        action="store_true",
        help="Log all messages, not just those from specified logging peers.",
    )

    # peer setup
    parser.add_argument(
        "-psd",
        "--peer-setup-delay",
        type=float,
        default=30.0,
        help="Delay in seconds before setting up late-start peers.",
    )
    parser.add_argument(
        "-n",
        "--n-peers",
        type=int,
        default=20,
        help="Number of peers to instantiate.",
    )
    parser.add_argument(
        "-nl",
        "--n-late-start-peers",
        type=float,
        default=0.1,
        help="Number of late-start peers to instantiate as a percentage of n_peers.",
    )
    parser.add_argument(
        "-sp",
        "--starting-port",
        type=int,
        default=5555 + randint(0, 1000),
        help="Starting port for peer addresses. (defaults to 5555+randint(1000))",
    )

    args = parser.parse_args()
    if args.log_level == "v":
        args.log_level = "DEBUG"

    return args
