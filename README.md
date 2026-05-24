# Safety First: Driving Simulator

A 2D Pygame driving simulator focused on road safety. The game rewards good driving habits such as lane discipline, proper signaling, safe overtaking, and obeying speed limits and traffic lights.

## Gameplay Demo

<video src="assets/Car_record.mp4" controls width="640"></video>

## Suggested GitHub Repo Name

`safety-first-driving-simulator`

## Suggested GitHub Description

A 2D road safety driving simulator built with Pygame, featuring lane discipline, speed limits, overtaking, tailgating checks, and traffic-light rules.

## Features

- Smooth lane steering and braking
- Dynamic speed limits
- Lane straddling detection
- Turn signal checks when changing lanes
- Tailgating warnings and penalties
- Overtake bonuses for safe passing
- Traffic light and crosswalk logic
- Optional sprite support for a more realistic look

## Requirements

- Python 3.10 or later
- Pygame

Install Pygame with:

```bash
pip install pygame
```

## How To Run

From the project folder:

```bash
python safety-drive-car-simulation.py
```

If `python` is not available on your system, use the Python launcher or your installed Python path instead.

## Controls

- `Up` or `W`: Accelerate
- `Down`, `S`, or `Space`: Brake
- `Left` or `A`: Steer left
- `Right` or `D`: Steer right
- `Q`: Toggle left blinker
- `E`: Toggle right blinker
- `H`: Honk
- `Enter` on the start screen: Start the game
- `R` on the game over screen: Restart

## Gameplay Rules

- Stay inside your lane and avoid straddling the divider lines
- Signal before changing lanes
- Follow the current speed limit
- Stop for red lights
- Overtake other cars safely on the left
- Avoid tailgating slower vehicles

## Optional Image Assets

If you want the game to look more realistic, create an `assets` folder next to `safety-drive-car-simulation.py` and add these files:

- `assets/player_car.png`
- `assets/npc_car.png`
- `assets/obstacle.png`

If those files are missing, the game will fall back to simple shape-based graphics automatically.

## Optional Audio Assets

Add these files to `assets/` for sound effects:

- `assets/honk.mp3`
- `assets/crash.mp3`
- `assets/powerup.mp3`

## File Structure

```text
Game_simulation/
  safety-drive-car-simulation.py
  README.md
  assets/
    player_car.png
    npc_car.png
    obstacle.png
```

## Notes

- The game uses Pygame's built-in drawing and sprite loading.
- The simulator is designed to be easy to extend with more vehicles, road signs, sounds, and better art assets.

## Push To GitHub

If you have not pushed this project yet, run these commands from the project folder:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/safety-first-driving-simulator.git
git push -u origin main
```

If your repository already exists on GitHub, replace the `origin` URL with your own repo link.