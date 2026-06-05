import asyncio
import importlib.util
from pathlib import Path


def load_game_module():
    game_path = Path(__file__).parent / "safety-drive-car-simulation.py"
    spec = importlib.util.spec_from_file_location("game_module", game_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    game_module = load_game_module()
    game = game_module.Game()

    while True:
        dt = game.clock.tick(game_module.FPS) / 1000.0
        game.step(dt)
        await asyncio.sleep(0)


if __name__ == "__main__":
    asyncio.run(main())
