#!/usr/bin/env python3
"""
Admin commands for game management.
Usage: python admin_commands.py [command]

Commands:
  cycle - Run the full game cycle resolution (includes ideology changes)
"""
import asyncio
import sys
import logging

from commands import run_game_cycle


async def run_cycle():
    """Run full game cycle resolution (includes ideology changes)"""
    print("Running full game cycle resolution (includes ideology changes)...")
    await run_game_cycle()
    print("Game cycle completed!")


async def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    command = sys.argv[1].lower()
    
    # Setup basic logging
    logging.basicConfig(level=logging.INFO)
    
    if command == "cycle":
        await run_cycle()
    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    asyncio.run(main())
