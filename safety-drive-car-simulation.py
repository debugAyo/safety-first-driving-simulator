import os
import pygame
import random
import sys
import math
from entities import Player, NPC, Obstacle

# ==========================================
# CONSTANTS & CONFIGURATION
# ==========================================
WIDTH, HEIGHT = 800, 600
FPS = 60

# Road Configuration
ROAD_LEFT = 150
ROAD_RIGHT = 650
LANE_WIDTH = (ROAD_RIGHT - ROAD_LEFT) / 3
LANE_CENTERS = [ROAD_LEFT + LANE_WIDTH * 0.5, ROAD_LEFT + LANE_WIDTH * 1.5, ROAD_LEFT + LANE_WIDTH * 2.5]
DIVIDERS = [ROAD_LEFT + LANE_WIDTH, ROAD_LEFT + LANE_WIDTH * 2]
LANE_INDEXES = [0, 1, 2]

# Colors
SKY = (24, 30, 36)
# Polished palette (requested)
ROAD_COLOR = (0x2a, 0x2a, 0x2a)       # #2a2a2a
CONE_ORANGE = (235, 140, 40)
LANE_YELLOW = (0xd4, 0xa0, 0x17)      # #d4a017
GRASS = (24, 120, 35)
ROAD_EDGE = (42, 42, 42)
HUD_PANEL = (12, 12, 12, 180)         # semi-transparent
TEXT = (230, 230, 230)
ACCENT = (224, 172, 80)
DANGER = (196, 58, 58)
SAFE = (79, 149, 87)
PLAYER_COLOR = (0, 153, 255)          # #0099ff
NPC_RED = (149, 57, 57)
OBSTACLE_AMBER = (190, 130, 54)
BLACK = (0, 0, 0)
POWERUP_BLUE = (80, 200, 255)
POWERUP_GREEN = (80, 220, 120)
POWERUP_PURPLE = (170, 90, 220)

POWERUP_TYPES = ["shield", "slowmo", "boost"]

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")


def load_sprite(name, size, fallback_color, colorkey=None):
    path = os.path.join(ASSET_DIR, name)
    if os.path.exists(path):
        image = pygame.image.load(path).convert_alpha()
        image = pygame.transform.smoothscale(image, size)
        if colorkey is not None:
            image.set_colorkey(colorkey)
        return image

    surface = pygame.Surface(size, pygame.SRCALPHA)
    surface.fill(fallback_color)
    return surface


def load_sound(name):
    path = os.path.join(ASSET_DIR, name)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None


def load_sound_any(base_name):
    for ext in (".ogg", ".mp3"):
        snd = load_sound(base_name + ext)
        if snd is not None:
            return snd
    return None


def load_music(base_name):
    # return path to music file if present, preferring .ogg then .mp3
    for ext in (".ogg", ".mp3"):
        path = os.path.join(ASSET_DIR, base_name + ext)
        if os.path.exists(path):
            return path
    return None


def wrap_angle(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


class Particle:
    def __init__(self, pos, vel, color, life=40):
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.color = color
        self.life = life
        self.max_life = life

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # gravity-ish
        self.life -= 1

    def draw(self, surf):
        if self.life <= 0: return
        a = max(0, int(255 * (self.life / self.max_life)))
        col = (self.color[0], self.color[1], self.color[2], a)
        s = pygame.Surface((4, 4), pygame.SRCALPHA)
        s.fill(col)
        surf.blit(s, (int(self.x), int(self.y)))

# ==========================================
# CLASSES
# ==========================================
class Powerup:
    def __init__(self, x, y, kind, sprite=None):
        self.kind = kind
        self.width = 26
        self.height = 26
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.sprite = sprite
    
    def update(self, dt, player_speed):
        self.y += (player_speed) * 3 * dt
        self.rect.center = (self.x, self.y)
    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        else:
            color = POWERUP_BLUE
            if self.kind == "shield":
                color = POWERUP_GREEN
            elif self.kind == "slowmo":
                color = POWERUP_PURPLE
            pygame.draw.circle(screen, color, self.rect.center, 12)
            pygame.draw.circle(screen, (255, 255, 255), self.rect.center, 12, 2)


class Crosswalk:
    def __init__(self, y_start):
        self.y = y_start
        self.height = 60
        self.state = "YELLOW" # Sequence: Yellow -> Red -> Green
        self.timer = 0
        self.penalized = False
        self.stop_line = pygame.Rect(ROAD_LEFT, self.y + self.height, ROAD_RIGHT - ROAD_LEFT, 10)

    def update(self, dt, player_speed):
        self.y += (player_speed) * 3 * dt
        self.stop_line.top = self.y + self.height

        self.timer += dt
        if self.state == "YELLOW" and self.timer > 2:
            self.state = "RED"
            self.timer = 0
        elif self.state == "RED" and self.timer > 5:
            self.state = "GREEN"
            self.timer = 0
        elif self.state == "GREEN" and self.timer > 5:
            self.state = "YELLOW"
            self.timer = 0

    def draw(self, screen):
        # Crosswalk stripes
        for i in range(ROAD_LEFT + 10, ROAD_RIGHT, 30):
            pygame.draw.rect(screen, LANE_YELLOW, (i, self.y, 20, self.height))
        # Stop line
        pygame.draw.rect(screen, LANE_YELLOW, self.stop_line)
        # Traffic Light box on the right side
        light_box = pygame.Rect(ROAD_RIGHT + 10, self.y, 30, 90)
        pygame.draw.rect(screen, ROAD_EDGE, light_box)

        c_red = DANGER if self.state == "RED" else (60, 22, 22)
        c_yel = ACCENT if self.state == "YELLOW" else (70, 58, 18)
        c_grn = SAFE if self.state == "GREEN" else (18, 54, 29)

        pygame.draw.circle(screen, c_red, (ROAD_RIGHT + 25, int(self.y) + 15), 10)
        pygame.draw.circle(screen, c_yel, (ROAD_RIGHT + 25, int(self.y) + 45), 10)
        pygame.draw.circle(screen, c_grn, (ROAD_RIGHT + 25, int(self.y) + 75), 10)

class ConstructionZone:
    def __init__(self, y_start):
        self.y = y_start
        self.height = 140
        self.active = True
        self.cones = []
        # place cones in random lane positions
        for _ in range(4):
            lane = random.choice(LANE_CENTERS)
            offset = random.randint(0, self.height - 20)
            self.cones.append((lane, self.y + offset))
    def update(self, dt, player_speed):
        self.y += player_speed * 3 * dt
        self.cones = [(x, y + player_speed * 3 * dt) for (x, y) in self.cones]
    def draw(self, screen):
        zone_rect = pygame.Rect(ROAD_LEFT, self.y, ROAD_RIGHT - ROAD_LEFT, self.height)
        pygame.draw.rect(screen, (60, 60, 60), zone_rect)
        for (x, y) in self.cones:
            pygame.draw.polygon(screen, CONE_ORANGE, [(x-6, y+12), (x+6, y+12), (x, y-12)])
    def draw(self, surf):
        # arena
        pygame.draw.rect(surf, (20, 24, 28), (self.x, self.y, self.w, self.h))
        # top instruction/rules bar
        header = pygame.Rect(self.x, self.y - 56, self.w, 52)
        pygame.draw.rect(surf, (22, 26, 32), header, border_radius=6)
        pygame.draw.rect(surf, (70, 70, 78), header, 1, border_radius=6)
        header_text = self.game.font.render(self.levels[self.level_index]["name"], True, TEXT)
        surf.blit(header_text, (self.x + 10, self.y - 64))
        objective_font = pygame.font.SysFont("Arial", 18, bold=True)
        objective_lines = []
        remaining = self.current_objective.strip()
        max_objective_width = self.w - 180
        while remaining:
            words = remaining.split()
            line = words[0]
            next_index = 1
            while next_index < len(words) and objective_font.size(f"{line} {words[next_index]}")[0] <= max_objective_width:
                line = f"{line} {words[next_index]}"
                next_index += 1
            objective_lines.append(line)
            remaining = " ".join(words[next_index:])
        objective_y = self.y - 40
        for line in objective_lines[:2]:
            obj_text = objective_font.render(line, True, ACCENT)
            surf.blit(obj_text, (self.x + 10, objective_y))
            objective_y += 20
        # draw parking target (improved visuals)
        if self.park_rect is not None:
            bay = self.park_rect
            pygame.draw.rect(surf, (30, 34, 38), bay, border_radius=6)
            # outer accent border
            pygame.draw.rect(surf, (220, 200, 120), bay, 3, border_radius=6)
            # inner dashed guide lines (vertical markers)
            marker_x1 = bay.left + 12
            marker_x2 = bay.right - 12
            step = 12
            for yy in range(bay.top + 8, bay.bottom - 8, step * 2):
                pygame.draw.line(surf, (200, 200, 200), (marker_x1, yy), (marker_x1, min(yy + step, bay.bottom - 8)), 2)
                pygame.draw.line(surf, (200, 200, 200), (marker_x2, yy), (marker_x2, min(yy + step, bay.bottom - 8)), 2)
            # guide stop line at bay bottom
            pygame.draw.line(surf, (255, 255, 255), (bay.left + 14, bay.bottom - 18), (bay.right - 14, bay.bottom - 18), 4)
        # draw tp zones
        if self.tp_forward is not None:
            pygame.draw.rect(surf, (32, 48, 40), self.tp_forward)
            pygame.draw.rect(surf, (32, 48, 40), self.tp_reverse)
            pygame.draw.rect(surf, (32, 48, 40), self.tp_final)
            pygame.draw.rect(surf, (200, 200, 200), self.tp_forward, 1)
            pygame.draw.rect(surf, (200, 200, 200), self.tp_reverse, 1)
            pygame.draw.rect(surf, (200, 200, 200), self.tp_final, 1)

        if self.checkpoints:
            for i, cp in enumerate(self.checkpoints):
                pygame.draw.rect(surf, (50, 60, 72), cp)
                pygame.draw.rect(surf, ACCENT if i == self.checkpoint_index else TEXT, cp, 2)

        # draw vehicle from actual image sprite with animated wheels
        rotated = self._render_vehicle_sprite()
        r = rotated.get_rect(center=(int(self.vehicle.x), int(self.vehicle.y)))
        r.y += int(self.vehicle.body_bob)
        surf.blit(rotated, r.topleft)

        # UI
        stat_box = pygame.Rect(self.x + self.w - 140, self.y - 62, 130, 52)
        pygame.draw.rect(surf, (12, 14, 18), stat_box, border_radius=8)
        pygame.draw.rect(surf, (60, 60, 70), stat_box, 1, border_radius=8)
        sc = objective_font.render(f"Score: {self.score}", True, ACCENT)
        surf.blit(sc, (stat_box.x + 10, stat_box.y + 6))
        grade_text = objective_font.render(f"Grade: {self.last_grade if self.last_grade is not None else '--'}", True, TEXT)
        surf.blit(grade_text, (stat_box.x + 10, stat_box.y + 28))
        if self.message:
            m = self.game.font.render(self.message, True, SAFE)
            surf.blit(m, (self.x + 8, self.y + self.h + 8))
        if self.last_grade_notes:
            note = self.game.font.render(self.last_grade_notes, True, TEXT)
            surf.blit(note, (self.x + 8, self.y + self.h + 34))

        # rules & progress panels — place to the right if space, otherwise stack below arena
        panel_w = 240
        panel_gap = 12
        panel_x = self.x + self.w + 10
        panel_y = self.y - 4
        stack_below = False
        if panel_x + panel_w > WIDTH - 10:
            # not enough room on the right — stack panels below the arena
            panel_x = self.x
            panel_y = self.y + self.h + 12
            stack_below = True

        rules_box = pygame.Rect(panel_x, panel_y, panel_w, 200)
        pygame.draw.rect(surf, (14, 16, 20), rules_box, border_radius=8)
        pygame.draw.rect(surf, (60, 60, 70), rules_box, 2, border_radius=8)
        surf.blit(self.game.font.render("Rules", True, ACCENT), (rules_box.x + 10, rules_box.y + 8))
        ry = rules_box.y + 40
        for rule in self.current_rules:
            rr = objective_font.render(f"- {rule}", True, TEXT)
            surf.blit(rr, (rules_box.x + 10, ry))
            ry += 22

        prog_box = pygame.Rect(panel_x, rules_box.y + rules_box.h + panel_gap, panel_w, 156)
        if stack_below and prog_box.y + prog_box.h > HEIGHT - 40:
            # if stacking would push prog box off-screen, reduce its height
            prog_box.h = max(120, HEIGHT - prog_box.y - 40)
        pygame.draw.rect(surf, (14, 16, 20), prog_box, border_radius=8)
        pygame.draw.rect(surf, (60, 60, 70), prog_box, 2, border_radius=8)
        surf.blit(self.game.font.render("Levels", True, ACCENT), (prog_box.x + 10, prog_box.y + 8))
        prog_lines = [
            f"Current: {self.level_index + 1}/{len(self.levels)}",
            f"Completed: {self.completed_levels}",
            f"Pass Mark: {self.levels[self.level_index]['pass_mark']}",
            f"Rules Broken: {self.rules_broken}",
        ]
        py = prog_box.y + 40
        for line in prog_lines:
            surf.blit(objective_font.render(line, True, TEXT), (prog_box.x + 10, py))
            py += 22

        if self.finished:
            done = self.game.big_font.render("PASS", True, SAFE)
            surf.blit(done, (self.x + self.w // 2 - done.get_width() // 2, self.y + 190))
            done2 = self.game.font.render("Press ESC to return to level select", True, TEXT)
            surf.blit(done2, (self.x + self.w // 2 - done2.get_width() // 2, self.y + 250))

        controls_box = pygame.Rect(self.x + self.w + 10, self.y + 372, 240, 128)
        pygame.draw.rect(surf, (14, 16, 20), controls_box, border_radius=8)
        pygame.draw.rect(surf, (60, 60, 70), controls_box, 2, border_radius=8)
        surf.blit(self.game.font.render("Controls", True, ACCENT), (controls_box.x + 10, controls_box.y + 8))
        control_lines = [
            "W / Up: Accelerate",
            "S / Down: Reverse",
            "A-D / Left-Right: Steer",
            "Esc: Back to select",
        ]
        cy = controls_box.y + 38
        for line in control_lines:
            surf.blit(objective_font.render(line, True, TEXT), (controls_box.x + 10, cy))
            cy += 20


# ==========================================
# MAIN GAME MANAGER
# ==========================================
class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error as e:
            print(f"Audio initialization failed: {e}. Continuing without sound.")
            pygame.mixer = None
        
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Safety First: 2D Driving Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)

        self.player_sprite = load_sprite("player_car.png", (40, 70), PLAYER_COLOR)
        self.npc_sprite = load_sprite("npc_car.png", (40, 70), NPC_RED)
        self.obstacle_sprite = load_sprite("obstacle.png", (24, 24), OBSTACLE_AMBER)
        self.snd_honk = load_sound_any("honk") if pygame.mixer else None
        self.snd_crash = load_sound_any("crash") if pygame.mixer else None
        self.snd_powerup = load_sound_any("powerup") if pygame.mixer else None
        
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

        self.state = "START"
        # UI / runtime state
        self.display_score = 100.0
        self.particles = []
        self.high_score = self.load_high_score()
        self.saved_high = False
        self.lives = 3
        self.red_light_active = False
        self.red_pulse = 0.0
        # Pause menu mouse state
        self.pause_buttons = []
        self.pause_hover = -1
        # Ensure the system mouse cursor is visible
        pygame.mouse.set_visible(True)
        # Music settings (initialize before any event handlers use them)
        try:
            self.music_path = load_music("theme")
        except Exception:
            self.music_path = None
        self.music_on = True if (self.music_path and pygame.mixer) else False
        self.music_volume = 0.6
        self.music_playing = False
        self.reset_game()

    def load_high_score(self):
        try:
            p = os.path.join(os.path.dirname(__file__), "highscore.txt")
            if os.path.exists(p):
                with open(p, "r") as f:
                    return int(f.read().strip() or 0)
        except Exception:
            pass
        return 0

    def save_high_score(self):
        try:
            p = os.path.join(os.path.dirname(__file__), "highscore.txt")
            with open(p, "w") as f:
                f.write(str(self.high_score))
        except Exception:
            pass

    # ----- Music control helpers -----
    def start_music(self):
        if not pygame.mixer or not self.music_path:
            return
        try:
            # load only once
            if not self.music_playing:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)
                self.music_playing = True
            else:
                pygame.mixer.music.unpause()
        except Exception:
            pass

    def stop_music(self):
        if not pygame.mixer:
            return
        try:
            pygame.mixer.music.stop()
            self.music_playing = False
        except Exception:
            pass

    def pause_music(self):
        if not pygame.mixer:
            return
        try:
            pygame.mixer.music.pause()
        except Exception:
            pass

    def unpause_music(self):
        if not pygame.mixer:
            return
        try:
            pygame.mixer.music.unpause()
        except Exception:
            pass

    def toggle_music(self):
        if not pygame.mixer or not self.music_path:
            return
        self.music_on = not getattr(self, 'music_on', True)
        if self.music_on:
            # resume or start
            if not self.music_playing:
                self.start_music()
            else:
                self.unpause_music()
        else:
            self.pause_music()

    def reset_game(self):
        self.player = Player(self.player_sprite)
        self.npcs = []
        self.obstacles = []
        self.crosswalks =[]
        self.scroll_y = 0
        self.powerups = []
        self.powerup_timer = 0.0
        self.base_max_speed = self.player.max_speed
        self.zones = []
        self.zone_timer = 0.0
        
        # Powerup effects
        self.shield_timer = 0.0
        self.slowmo_timer = 0.0
        self.boost_timer = 0.0

        # Spawning Timers
        self.npc_timer = 0
        self.obs_timer = 0
        self.crosswalk_timer = 0
        self.obs_spawn_delay = random.uniform(8.0, 12.0)
        self.crosswalk_spawn_delay = random.uniform(15.0, 20.0)
        
        # Safety Systems & Limits
        self.speed_limit = 50
        self.limit_timer = 0
        self.speeding_timer = 0
        
        self.player_lane = 1
        self.straddle_timer = 0
        self.tailgating_active = False
        self.tailgate_timer = 0

        # Scoring & Reporting
        self.safety_score = 100
        self.infractions = {
            "straddling": 0,
            "no_blinker": 0,
            "red_light": 0,
            "tailgating": 0,
            "speeding": 0
        }
        self.bonuses = {"clean_overtake": 0}
        self.messages =[]  # UI Floating text
        # Time limit (seconds) for the session; 0 means no limit
        self.level_time_limit = 120
        self.time_left = float(self.level_time_limit)
        self.display_score = float(self.safety_score)
        self.particles = []
        self.saved_high = False
        # reset pause UI state
        self.pause_buttons = []
        self.pause_hover = -1

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)

    def step(self, dt):
        self.handle_events()

        if self.state == "START":
            self.draw_start_screen()
        elif self.state == "PLAY":
            self.update_play(dt)
            self.draw_play()
        elif self.state == "PAUSE":
            # Render the current play frame but do not update game logic
            self.draw_play()
            self.draw_pause_menu()
        elif self.state == "GAME_OVER":
            self.draw_game_over()

        # Finished drawing current state

        pygame.display.flip()

    

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Mouse handling for pause menu
            if event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                # hover detection for pause menu
                if self.state == "PAUSE":
                    hover = -1
                    for i, b in enumerate(self.pause_buttons):
                        if b[1].collidepoint(mx, my):
                            hover = i
                            break
                    self.pause_hover = hover
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "PAUSE" and event.button == 1:
                    mx, my = event.pos
                    for label, rect in self.pause_buttons:
                        if rect.collidepoint(mx, my):
                            if label == "Resume":
                                self.state = "PLAY"
                                self.unpause_music()
                            elif label == "Restart":
                                self.reset_game()
                                self.state = "PLAY"
                                if self.music_on:
                                    self.start_music()
                            elif label == "Quit":
                                self.reset_game()
                                self.state = "START"
                                self.stop_music()
                            elif label.startswith("Music"):
                                self.toggle_music()
                            break
            if event.type == pygame.KEYDOWN:
                # Music toggle key
                if event.key == pygame.K_m:
                    self.toggle_music()
                    continue

                # Universal play/pause toggle (when in PLAY/PAUSE)
                if event.key in (pygame.K_ESCAPE, pygame.K_p) and self.state in ("PLAY", "PAUSE"):
                    # toggle state and music pause/unpause
                    if self.state == "PLAY":
                        self.state = "PAUSE"
                        self.pause_music()
                    else:
                        self.state = "PLAY"
                        if self.music_on:
                            self.unpause_music()
                    continue

                if self.state == "START" and event.key == pygame.K_RETURN:
                    self.state = "PLAY"
                    if self.music_on:
                        self.start_music()
                elif self.state == "GAME_OVER" and event.key == pygame.K_r:
                    self.reset_game()
                    self.state = "PLAY"
                    if self.music_on:
                        self.start_music()
                elif self.state == "PLAY":
                    if event.key == pygame.K_h and self.snd_honk is not None:
                        self.snd_honk.play()
                    # Indicator Toggles
                    if event.key == pygame.K_q:
                        self.player.blinker = -1 if self.player.blinker != -1 else 0
                    elif event.key == pygame.K_e:
                        self.player.blinker = 1 if self.player.blinker != 1 else 0
                elif self.state == "PAUSE":
                    # Pause menu shortcuts
                    if event.key == pygame.K_r:
                        self.reset_game()
                        self.state = "PLAY"
                        if self.music_on:
                            self.start_music()
                    elif event.key == pygame.K_q:
                        # Quit to start screen
                        self.reset_game()
                        self.state = "START"

    def add_message(self, text, color):
        self.messages.append({"text": text, "color": color, "timer": 2.0})

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.joystick)
        speed_scale = 0.6 if self.slowmo_timer > 0 else 1.0
        self.world_speed = self.player.speed * speed_scale
        self.zone_timer += dt
        if self.zone_timer > 20.0:
            self.zone_timer = 0
            self.zones.append(ConstructionZone(-200))

        # Background scroll
        self.scroll_y += self.world_speed * 3 * dt
        if self.scroll_y >= 60:
            self.scroll_y -= 60

        # --- SPAWN LOGIC ---
        self.npc_timer += dt
        if self.npc_timer > max(1.0, 3.0 - (self.world_speed / 100.0)):
            self.npc_timer = 0
            lane = random.choice(LANE_CENTERS)
            npc_speed = random.randint(30, 60)
            self.npcs.append(NPC(lane, -100, npc_speed, self.npc_sprite))

        self.obs_timer += dt
        if self.obs_timer > self.obs_spawn_delay:
            self.obs_timer = 0
            self.obs_spawn_delay = random.uniform(8.0, 12.0)
            lane = random.choice(LANE_CENTERS) + random.randint(-20, 20)
            self.obstacles.append(Obstacle(lane, -100, self.obstacle_sprite))
            
        # Powerup spawn
        self.powerup_timer += dt
        if self.powerup_timer > 12.0:
            self.powerup_timer = 0
            lane = random.choice(LANE_CENTERS)
            kind = random.choice(POWERUP_TYPES)
            self.powerups.append(Powerup(lane, -120, kind))

        self.crosswalk_timer += dt
        if self.crosswalk_timer > self.crosswalk_spawn_delay:
            self.crosswalk_timer = 0
            self.crosswalk_spawn_delay = random.uniform(15.0, 20.0)
            self.crosswalks.append(Crosswalk(-200))

        # --- UPDATE ENTITIES ---
        for npc in self.npcs[:]:
            npc.update(dt, self.world_speed)
            if npc.y > HEIGHT + 100:
                self.npcs.remove(npc)
            elif npc.crashed and npc.crash_timer <= 0:
                self.npcs.remove(npc)
        for npc in self.npcs:
            if npc.crashed and random.random() < 0.2:
                sx = npc.rect.centerx + random.uniform(-8, 8)
                sy = npc.rect.top + random.uniform(-6, 6)
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(-2.0, -0.5)
                self.particles.append(Particle((sx, sy), (vx, vy), (140, 140, 140), life=30))
        for obs in self.obstacles[:]:
            obs.update(dt, self.world_speed)
            if obs.y > HEIGHT + 100: self.obstacles.remove(obs)
        for cw in self.crosswalks[:]:
            cw.update(dt, self.world_speed)
            if cw.y > HEIGHT + 100: self.crosswalks.remove(cw)
        for z in self.zones[:]:
            z.update(dt, self.world_speed)
            if z.y > HEIGHT + 200:
                self.zones.remove(z)
        for p in self.powerups[:]:
            p.update(dt, self.world_speed)
            if p.y > HEIGHT + 100:
                self.powerups.remove(p)
        if self.shield_timer > 0:
            self.shield_timer -=dt
        if self.slowmo_timer > 0:
            self.slowmo_timer -= dt
        if self.boost_timer > 0:
            self.boost_timer -=dt
        if self.boost_timer > 0:
            self.player.max_speed = self.base_max_speed + 30
            self.player.speed = min(self.player.speed + 40 * dt, self.player.max_speed)
        else:
            self.player.max_speed = self.base_max_speed
        
        def lane_clear(target_lane, ref_y):
            lane_x = LANE_CENTERS[target_lane]
            for other in self.npcs:
                if other.lane != target_lane:
                    continue
                if abs(other.y - ref_y) < 140:
                    return False
            for obs in self.obstacles:
                if abs(obs.x - lane_x) < LANE_WIDTH / 3 and 0 < (obs.y - ref_y) < 140:
                    return False
            return True

        for npc in self.npcs:
            if npc.crashed:
                continue
            hazard_ahead = False
            for other in self.npcs:
                if other is npc:
                    continue
                same_lane = abs(other.x - npc.x) < LANE_WIDTH / 3
                ahead = 0 < (other.y - npc.y) < 140
                if same_lane and ahead:
                    hazard_ahead = True
                    break
            if not hazard_ahead:
                for obs in self.obstacles:
                    same_lane = abs(obs.x - npc.x) < LANE_WIDTH / 3
                    ahead = 0 < (obs.y - npc.y) < 140
                    if same_lane and ahead:
                        hazard_ahead = True
                        break
            if hazard_ahead:
                if npc.lane > 0 and lane_clear(npc.lane - 1, npc.y):
                    npc.try_lane_change(npc.lane - 1)
                elif npc.lane < 2 and lane_clear(npc.lane + 1, npc.y):
                    npc.try_lane_change(npc.lane + 1)
        
        for p in self.powerups[:]:
            if self.player.rect.colliderect(p.rect):
                if p.kind == "shield":
                    self.shield_timer = 6.0
                    self.add_message("Shield Activate!", SAFE)
                elif p.kind == "slowmo":
                    self.slowmo_timer = 5.0
                    self.add_message("Slow Motion!", POWERUP_PURPLE)
                elif p.kind == "boost":
                    self.boost_timer = 5.0
                    self.add_message("Speed Boost!", ACCENT)
                if self.snd_powerup is not None:
                    self.snd_powerup.play()
                self.powerups.remove(p)


        self.check_npc_collisions()

        # --- SAFETY SYSTEMS LOGIC ---
        self.check_lane_discipline(dt)
        self.check_speed_limit(dt)
        self.check_tailgating(dt)
        self.check_overtaking()
        self.check_collisions()

        # Update floating messages
        for msg in self.messages[:]:
            msg["timer"] -= dt
            if msg["timer"] <= 0:
                self.messages.remove(msg)

        # Animate displayed score toward actual score
        self.display_score += (self.safety_score - self.display_score) * min(10 * dt, 1)

        # Update particles
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        # Red light detection (any visible crosswalk in RED)
        self.red_light_active = False
        for cw in self.crosswalks:
            if cw.state == "RED" and -200 < cw.y < HEIGHT:
                self.red_light_active = True
                break
        # Construction Zone speed Limit Override
        in_zone = False
        for z in self.zones:
            if z.y < self.player.y < z.y + z.height:
                in_zone = True
                break
        if in_zone:
            self.speed_limit = min(self.speed_limit, 30)

        # Pulse value
        if self.red_light_active:
            self.red_pulse += dt * 3.0
        else:
            self.red_pulse = 0.0

        # Time limit handling
        if self.level_time_limit and self.state == "PLAY":
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                if self.safety_score > self.high_score:
                    self.high_score = int(self.safety_score)
                    self.save_high_score()
                self.state = "GAME_OVER"
                return
    
    def check_npc_collisions(self):
        for i in range(len(self.npcs)):
            for j in range(i + 1, len(self.npcs)):
                a = self.npcs[i]
                b = self.npcs[j]
                if a.crashed or b.crashed:
                    continue
                if a.rect.colliderect(b.rect):
                    a.crashed = True
                    b.crashed = True
                    a.crash_timer = 3.0
                    b.crash_timer = 3.0

                    cx, cy = a.rect.centerx, a.rect.centery
                    for _ in range(30):
                        vx = random.uniform(-5, 5)
                        vy = random.uniform(-5, 2)
                        col = random.choice([NPC_RED, OBSTACLE_AMBER])
                        self.particles.append(Particle((cx, cy), (vx, vy), col, life=40))

    def check_lane_discipline(self, dt):
        # Identify current lane (0, 1, 2)
        current_lane = int((self.player.x - ROAD_LEFT) // LANE_WIDTH)
        current_lane = max(0, min(2, current_lane))

        # Indicator Logic upon changing lanes
        if current_lane != self.player_lane:
            if current_lane < self.player_lane and self.player.blinker != -1:
                self.safety_score -= 10
                self.infractions["no_blinker"] += 10
                self.add_message("Failed to Indicate! -10", DANGER)
            elif current_lane > self.player_lane and self.player.blinker != 1:
                self.safety_score -= 10
                self.infractions["no_blinker"] += 10
                self.add_message("Failed to Indicate! -10", DANGER)
            
            self.player_lane = current_lane
            self.player.blinker = 0  # Auto turn off blinker

        # Lane Straddling Logic
        dist1 = abs(self.player.x - DIVIDERS[0])
        dist2 = abs(self.player.x - DIVIDERS[1])
        if dist1 < 25 or dist2 < 25:
            self.straddle_timer += dt
            if self.straddle_timer > 2.0:
                self.safety_score -= 5
                self.infractions["straddling"] += 5
                self.add_message("Lane Straddling! -5", DANGER)
                self.straddle_timer = 0
        else:
            self.straddle_timer = 0

    def check_speed_limit(self, dt):
        self.limit_timer += dt
        if self.limit_timer > 10.0:
            self.speed_limit = random.choice([30, 50, 70, 90])
            self.limit_timer = 0

        if self.player.speed > self.speed_limit:
            self.speeding_timer += dt
            if self.speeding_timer > 2.0:  # Penalize every 2 seconds of speeding
                self.safety_score -= 2
                self.infractions["speeding"] += 2
                self.add_message("Speeding! -2", DANGER)
                self.speeding_timer = 0
        else:
            self.speeding_timer = 0

    def check_tailgating(self, dt):
        self.tailgating_active = False
        for npc in self.npcs:
            if abs(npc.x - self.player.x) < LANE_WIDTH/2: # Same lane
                dist = self.player.y - npc.y # Forward distance
                if 0 < dist < 100 and not self.player.braking and self.player.speed > npc.speed:
                    self.tailgating_active = True
                    self.tailgate_timer += dt
                    if self.tailgate_timer > 1.0:
                        self.safety_score -= 2
                        self.infractions["tailgating"] += 2
                        self.tailgate_timer = 0
                    break
        if not self.tailgating_active:
            self.tailgate_timer = 0

    def check_overtaking(self):
        for npc in self.npcs:
            if not npc.passed and npc.y > self.player.y + self.player.height:
                npc.passed = True
                # Clean overtake on the Left side (Nigeria / Right-Hand traffic standard)
                if self.player.x < npc.x - 30: 
                    self.safety_score += 5
                    self.bonuses["clean_overtake"] += 5
                    self.add_message("Clean Overtake! +5", ACCENT)

    def check_collisions(self):
        # Crash with Cars/Obstacles
        for npc in self.npcs:
            if self.player.rect.colliderect(npc.rect):
                # spawn particles at collision
                cx, cy = self.player.rect.center
                for _ in range(40):
                    vx = random.uniform(-6, 6)
                    vy = random.uniform(-4, 2)
                    col = random.choice([PLAYER_COLOR, NPC_RED, OBSTACLE_AMBER])
                    self.particles.append(Particle((cx, cy), (vx, vy), col, life=40))
                if self.shield_timer > 0:
                    self.shield_timer = 0
                    self.add_message("Shield Saved You!", SAFE)
                    self.npcs.remove(npc)
                    return

                # preserve existing behavior
                if self.snd_crash is not None:
                    self.snd_crash.play()
                if self.safety_score > self.high_score:
                    self.high_score = int(self.safety_score)
                    self.save_high_score()
                self.state = "GAME_OVER"
                return
        for obs in self.obstacles:
            if self.player.rect.colliderect(obs.rect):
                cx, cy = self.player.rect.center
                for _ in range(30):
                    vx = random.uniform(-5, 5)
                    vy = random.uniform(-5, 1)
                    col = random.choice([PLAYER_COLOR, OBSTACLE_AMBER])
                    self.particles.append(Particle((cx, cy), (vx, vy), col, life=40))
                if self.shield_timer > 0:
                    self.shield_timer = 0
                    self.add_message("Shield Saved You!", SAFE)
                    self.obstacles.remove(obs)
                    return

                if self.snd_crash is not None:
                    self.snd_crash.play()
                if self.safety_score > self.high_score:
                    self.high_score = int(self.safety_score)
                    self.save_high_score()
                self.state = "GAME_OVER"
                return

               
                
        # Intersection Stop Line (Ran Red Light)
        for cw in self.crosswalks:
            if cw.stop_line.colliderect(self.player.rect) and cw.state == "RED" and not cw.penalized:
                self.safety_score -= 20
                self.infractions["red_light"] += 20
                self.add_message("Ran Red Light! -20", DANGER)
                cw.penalized = True

    def draw_play(self):
        for z in self.zones:
            z.draw(self.screen)

        # Sky sidebars
        self.screen.fill(SKY)

        # Grass / roadside
        pygame.draw.rect(self.screen, GRASS, (0, 0, ROAD_LEFT, HEIGHT))
        pygame.draw.rect(self.screen, GRASS, (ROAD_RIGHT, 0, WIDTH - ROAD_RIGHT, HEIGHT))

        # Road
        pygame.draw.rect(self.screen, ROAD_COLOR, (ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, HEIGHT))
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_LEFT - 18, 0, 18, HEIGHT))
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_RIGHT, 0, 18, HEIGHT))

        # Lane dividers (dashed)
        pygame.draw.line(self.screen, LANE_YELLOW, (ROAD_LEFT, 0), (ROAD_LEFT, HEIGHT), 4)
        pygame.draw.line(self.screen, LANE_YELLOW, (ROAD_RIGHT, 0), (ROAD_RIGHT, HEIGHT), 4)
        for div_x in DIVIDERS:
            for y in range(-120, HEIGHT + 60, 60):
                y1 = y + int(self.scroll_y)
                pygame.draw.line(self.screen, LANE_YELLOW, (div_x, y1), (div_x, y1 + 30), 6)

        # Crosswalks and entities
        for cw in self.crosswalks:
            cw.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        for p in self.powerups:
            p.draw(self.screen)
        for npc in self.npcs:
            npc.draw(self.screen)
        self.player.draw(self.screen)

        # Particles (on top of entities)
        for p in self.particles:
            p.draw(self.screen)

        # Red light overlay + banner
        if self.red_light_active:
            pulse = (0.5 + 0.5 * math.sin(self.red_pulse))
            overlay = pygame.Surface((ROAD_RIGHT - ROAD_LEFT, HEIGHT), pygame.SRCALPHA)
            overlay.fill((200, 30, 30, int(80 * pulse)))
            self.screen.blit(overlay, (ROAD_LEFT, 0))

            # Banner across road area
            banner_h = 60
            banner = pygame.Surface((ROAD_RIGHT - ROAD_LEFT, banner_h), pygame.SRCALPHA)
            banner.fill((200, 20, 20, int(200 * pulse)))
            self.screen.blit(banner, (ROAD_LEFT, HEIGHT//2 - banner_h//2))
            txt = self.big_font.render("RED LIGHT — STOP", True, TEXT)
            self.screen.blit(txt, (ROAD_LEFT + (ROAD_RIGHT-ROAD_LEFT)//2 - txt.get_width()//2, HEIGHT//2 - txt.get_height()//2))

        self.draw_hud()

    def draw_hud(self):
        # HUD panel
        panel = pygame.Surface((WIDTH - 20, 80), pygame.SRCALPHA)
        panel.fill(HUD_PANEL)
        self.screen.blit(panel, (10, 10))

        # Animated score (left)
        score_text = self.big_font.render(str(int(self.display_score)), True, TEXT)
        self.screen.blit(score_text, (20, 12))
        best_text = self.font.render(f"Best: {self.high_score}", True, ACCENT)
        self.screen.blit(best_text, (20, 12 + score_text.get_height() + 4))

        # Time-left display
        if self.level_time_limit and self.state == "PLAY":
            mins = int(self.time_left) // 60
            secs = int(self.time_left) % 60
            time_s = f"Time: {mins:02d}:{secs:02d}"
            time_text = self.font.render(time_s, True, TEXT)
            self.screen.blit(time_text, (20 + score_text.get_width() + 12, 20))

        # Top-right: lives (hearts) and current speed
        # Draw hearts (shift left to avoid overlap with limit)
        heart_x = WIDTH - 24
        heart_y = 18
        for i in range(self.lives):
            hx = heart_x - i * 24
            pygame.draw.circle(self.screen, DANGER, (hx - 18, heart_y + 12), 6)
            pygame.draw.polygon(self.screen, DANGER, [(hx-24, heart_y+12), (hx-18, heart_y+20), (hx-12, heart_y+12)])

        speed_text = self.font.render(f"SPD: {int(self.player.speed)}", True, TEXT)
        self.screen.blit(speed_text, (WIDTH - 200, 12 + score_text.get_height()))

        # Speed limit indicator (right-top corner area)
        flash_bg = ACCENT
        if self.player.speed > self.speed_limit and (pygame.time.get_ticks() // 250) % 2 == 0:
            flash_bg = DANGER
        limit_rect = pygame.Rect(WIDTH - 140, 16, 120, 48)
        # use an alpha surface to draw semi-transparent background
        limit_surf = pygame.Surface((limit_rect.w, limit_rect.h), pygame.SRCALPHA)
        limit_surf.fill((20, 20, 20, 200))
        # draw circular background for the numeric value
        pygame.draw.circle(limit_surf, flash_bg, (limit_rect.w - 36, limit_rect.h//2), 18)
        self.screen.blit(limit_surf, limit_rect.topleft)
        lim = self.font.render(f"LIMIT {self.speed_limit}", True, TEXT)
        self.screen.blit(lim, (limit_rect.left + 8, limit_rect.top + 10))

        # Warnings
        if self.tailgating_active:
            warning_surf = self.big_font.render("TAILGATING WARNING!", True, DANGER)
            self.screen.blit(warning_surf, (WIDTH//2 - warning_surf.get_width()//2, HEIGHT//2 - 100))
        
        active = []
        if self.shield_timer > 0: active.append("SHIELD")
        if self.slowmo_timer > 0: active.append("SLOW")
        if self.boost_timer > 0: active.append("BOOST")
        if active:
            txt = self.font.render("POWER: " + " | ".join(active), True, ACCENT)
            self.screen.blit(txt, (WIDTH//2 - txt.get_width()//2, 16))
        

        # Floating Messages
        y_offset = 100
        for msg in self.messages:
            msg_surf = self.font.render(msg["text"], True, msg["color"])
            self.screen.blit(msg_surf, (20, y_offset))
            y_offset += 26

        # Tips panel (in-play)
        tips = [
            "Navigation — Use eyes on horizon to steer smoothly.",
            "Plan lane changes early; signal before you move.",
            "Scan ahead for obstacles and brake early.",
        ]
        t_w = 360
        t_h = 84
        tip_surf = pygame.Surface((t_w, t_h), pygame.SRCALPHA)
        tip_surf.fill(HUD_PANEL)
        bx = 20
        by = 140
        self.screen.blit(tip_surf, (bx, by))
        ty = by + 8
        for t in tips:
            line = self.font.render("- " + t, True, TEXT)
            self.screen.blit(line, (bx + 8, ty))
            ty += 24

        # Controls panel (bottom-left)
        ctrl_lines = [
            "Controls:",
            "← / → : Change lanes",
            "↑ / W : Accelerate",
            "↓ / S / Space : Brake",
            "Q / E : Left / Right signal",
        ]
        cw = 300
        ch = 120
        ctrl_s = pygame.Surface((cw, ch), pygame.SRCALPHA)
        ctrl_s.fill(HUD_PANEL)
        ctrl_x = 20
        ctrl_y = HEIGHT - ch - 20
        self.screen.blit(ctrl_s, (ctrl_x, ctrl_y))
        ly = ctrl_y + 8
        for i, line in enumerate(ctrl_lines):
            color = ACCENT if i == 0 else TEXT
            txt = self.font.render(line, True, color)
            self.screen.blit(txt, (ctrl_x + 10, ly))
            ly += 22

    def draw_pause_menu(self):
        # Semi-transparent full-screen overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 6, 8, 180))
        self.screen.blit(overlay, (0, 0))

        box_w = 540
        box_h = 320
        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((18, 18, 20, 240))
        bx = WIDTH//2 - box_w//2
        by = HEIGHT//2 - box_h//2
        self.screen.blit(box, (bx, by))

        title = self.big_font.render("PAUSED", True, ACCENT)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, by + 20))
        # Buttons (clickable)
        btn_w = 220
        btn_h = 46
        btn_x = WIDTH//2 - btn_w//2
        start_y = by + 100
        labels = ["Resume", "Restart", "Quit", f"Music: {'On' if getattr(self, 'music_on', True) else 'Off'}"]
        self.pause_buttons = []
        for i, lbl in enumerate(labels):
            r = pygame.Rect(btn_x, start_y + i * (btn_h + 12), btn_w, btn_h)
            hovered = (self.pause_hover == i)
            col = (40, 40, 44) if not hovered else (64, 64, 72)
            pygame.draw.rect(self.screen, col, r, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT if hovered else (30, 30, 34), r, 2, border_radius=8)
            txt = self.font.render(lbl, True, TEXT)
            self.screen.blit(txt, (r.centerx - txt.get_width()//2, r.centery - txt.get_height()//2))
            self.pause_buttons.append((lbl, r))

        # Controls/info block below buttons
        ctrl_y = start_y + len(labels) * (btn_h + 12) + 10
        info_lines = [
            "Resume: Esc / P",
            "Restart: R",
            "Quit to Menu: Q",
            "",
            "Controls:",
            "← / → : Change lanes",
            "↑ / W : Accelerate",
            "↓ / S / Space : Brake",
            "Q / E : Left / Right signal",
        ]
        ty = ctrl_y
        for i, l in enumerate(info_lines):
            color = ACCENT if i == 4 else TEXT
            txt = self.font.render(l, True, color)
            self.screen.blit(txt, (bx + 30, ty))
            ty += 22

    

    def draw_start_screen(self):
        # Dashboard-style title screen
        for y in range(HEIGHT):
            shade = 16 + int(20 * (y / HEIGHT))
            self.screen.fill((shade, shade + 2, shade + 4), rect=pygame.Rect(0, y, WIDTH, 1))

        # Dashboard arc
        dash_rect = pygame.Rect(80, 120, WIDTH - 160, HEIGHT - 140)
        pygame.draw.ellipse(self.screen, (22, 22, 26), dash_rect)
        pygame.draw.ellipse(self.screen, (36, 36, 42), dash_rect, 4)

        # Speedometer
        center = (WIDTH // 2, HEIGHT // 2 + 40)
        pygame.draw.circle(self.screen, (12, 12, 16), center, 140)
        pygame.draw.circle(self.screen, (60, 60, 70), center, 140, 4)
        for i in range(0, 181, 20):
            angle = math.radians(180 + i)
            x1 = center[0] + int(math.cos(angle) * 120)
            y1 = center[1] + int(math.sin(angle) * 120)
            x2 = center[0] + int(math.cos(angle) * 135)
            y2 = center[1] + int(math.sin(angle) * 135)
            pygame.draw.line(self.screen, (90, 90, 100), (x1, y1), (x2, y2), 3)

        # Needle
        t = pygame.time.get_ticks() / 1000.0
        needle_angle = math.radians(210 + 30 * math.sin(t))
        nx = center[0] + int(math.cos(needle_angle) * 90)
        ny = center[1] + int(math.sin(needle_angle) * 90)
        pygame.draw.line(self.screen, ACCENT, center, (nx, ny), 4)
        pygame.draw.circle(self.screen, ACCENT, center, 6)

        title = self.big_font.render("Safety First", True, TEXT)
        subtitle = self.font.render("Driving Simulator", True, ACCENT)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
        self.screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 105))

        panel_w = 620
        panel_h = 180
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 10, 12, 210))
        px = WIDTH//2 - panel_w//2
        py = HEIGHT - panel_h - 40
        self.screen.blit(panel, (px, py))

        instr_lines = [
            "Steer: Left / Right or A / D",
            "Accelerate: Up / W    Brake: Down / S / Space",
            "Signals: Q / E   Follow speed limits and lights",
        ]
        ly = py + 18
        for line in instr_lines:
            r = self.font.render(line, True, TEXT)
            self.screen.blit(r, (px + 20, ly))
            ly += 32

        prompt = self.font.render("Press ENTER to Start", True, PLAYER_COLOR)
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, py + panel_h - 40))

    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 8, 8, 180))
        self.screen.blit(overlay, (0, 0))

        box_w = 640
        box_h = 420
        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((18, 18, 20, 230))
        bx = WIDTH//2 - box_w//2
        by = HEIGHT//2 - box_h//2
        self.screen.blit(box, (bx, by))

        title = self.big_font.render("GAME OVER", True, DANGER)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, by + 20))

        final = self.font.render(f"Final Score: {self.safety_score}", True, TEXT)
        best = self.font.render(f"High Score: {self.high_score}", True, ACCENT)
        self.screen.blit(final, (bx + 30, by + 110))
        self.screen.blit(best, (bx + 30, by + 150))

        # Safety tips
        tips = [
            "1. Always signal before changing lanes.",
            "2. Keep a safe following distance.",
            "3. Obey traffic lights and signs.",
            "4. Slow down in pedestrian areas.",
        ]
        ty = by + 200
        for t in tips:
            t_surf = self.font.render(t, True, TEXT)
            self.screen.blit(t_surf, (bx + 30, ty))
            ty += 36

        prompt = self.font.render("Press R to Restart", True, ACCENT)
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, by + box_h - 60))

if __name__ == "__main__":
    game = Game()
    game.run()