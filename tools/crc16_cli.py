"""CLI for generating CH9120 command frames."""

import argparse

from light_alarm.devices.protocol import build_command


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a CH9120 HEX command with CRC-16")
    parser.add_argument("--f", "--flash", dest="flash", required=True)
    parser.add_argument("--v", "--volume", dest="volume", required=True)
    parser.add_argument("--p", "--play", dest="play", required=True)
    parser.add_argument("--t", "--track", dest="track", required=True)
    args = parser.parse_args(argv)
    try:
        command = build_command(args.flash, args.volume, args.play, args.track)
    except ValueError as error:
        parser.error(str(error))
    print(f"The CRC value is: {command[-4:]}")
    print(f"The hex command: {command}")


if __name__ == "__main__":
    main()
