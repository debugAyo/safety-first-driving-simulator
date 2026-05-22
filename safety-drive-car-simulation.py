import os
import pygame
import random
import sys
import math

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

# Colors
SKY = (24, 30, 36)
# Polished palette (requested)
ROAD_COLOR = (0x2a, 0x2a, 0x2a)       # #2a2a2a
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
class Player:
    def __init__(self, sprite=None):
        self.width = 40
        self.height = 70
        self.x = ROAD_LEFT + LANE_WIDTH * 1.5  # Start in center lane
        self.y = HEIGHT - 150
        self.vx = 0
        self.speed = 0          # Current forward speed (MPH equivalent)
        self.max_speed = 120
        self.blinker = 0        # -1 = Left, 1 = Right, 0 = Off
        self.braking = False
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.sprite = sprite

    def update(self, dt, keys, joystick):
        # 1. Smooth Steering via Interpolation
        axis_x = 0
        if joystick and joystick.get_numaxes() > 0:
            axis_x = joystick.get_axis(0)
            if abs(axis_x) < 0.1: 
                axis_x = 0  # Deadzone
                
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: axis_x = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: axis_x = 1

        target_vx = axis_x * 250  # Max lateral speed
        self.vx += (target_vx - self.vx) * 6.0 * dt  # Lerp for smooth steering
        self.x += self.vx * dt

        # 2. Acceleration & Braking
        self.braking = keys[pygame.K_SPACE] or keys[pygame.K_DOWN] or keys[pygame.K_s]
        if joystick and joystick.get_numbuttons() > 0:
            if joystick.get_button(0): 
                self.braking = True

        accel = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]: 
            accel = 60
        if self.braking: 
            accel = -120

        self.speed += accel * dt
        if accel == 0: 
            self.speed -= 25 * dt  # Friction
            
        self.speed = max(0, min(self.speed, self.max_speed))

        # 3. Boundaries & Rect Update
        self.x = max(ROAD_LEFT + self.width/2, min(ROAD_RIGHT - self.width/2, self.x))
        self.rect.center = (self.x, self.y)

    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        else:
            pygame.draw.rect(screen, PLAYER_COLOR, self.rect, border_radius=6)

        if self.braking:
            pygame.draw.rect(screen, DANGER, (self.rect.left + 5, self.rect.bottom - 10, 10, 5))
            pygame.draw.rect(screen, DANGER, (self.rect.right - 15, self.rect.bottom - 10, 10, 5))

        t = pygame.time.get_ticks()
        if self.blinker == -1 and (t // 300) % 2 == 0:
            pygame.draw.rect(screen, ACCENT, (self.rect.left - 10, self.rect.top, 10, 10))
        elif self.blinker == 1 and (t // 300) % 2 == 0:
            pygame.draw.rect(screen, ACCENT, (self.rect.right, self.rect.top, 10, 10))

class NPC:
    def __init__(self, x, y, speed, sprite=None):
        self.width = 40
        self.height = 70
        self.x = x
        self.y = y
        self.speed = speed
        self.passed = False  # Track if player overtook this NPC
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.sprite = sprite

    def update(self, dt, player_speed):
        # NPC moves down screen based on player's speed vs NPC's speed
        self.y += (player_speed - self.speed) * 3 * dt 
        self.rect.center = (self.x, self.y)

    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        else:
            pygame.draw.rect(screen, NPC_RED, self.rect, border_radius=6)

class Obstacle:
    def __init__(self, x, y, sprite=None):
        self.width = 20
        self.height = 20
        self.x = x
        self.y = y
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.sprite = sprite

    def update(self, dt, player_speed):
        # Stationary relative to road, so moves down purely at player speed
        self.y += (player_speed) * 3 * dt
        self.rect.center = (self.x, self.y)

    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        else:
            pygame.draw.rect(screen, OBSTACLE_AMBER, self.rect, border_radius=4)

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

# ==========================================
# MAIN GAME MANAGER
# ==========================================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Safety First: 2D Driving Simulator")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24, bold=True)
        self.big_font = pygame.font.SysFont("Arial", 48, bold=True)

        self.player_sprite = load_sprite("player_car.png", (40, 70), PLAYER_COLOR)
        self.npc_sprite = load_sprite("npc_car.png", (40, 70), NPC_RED)
        self.obstacle_sprite = load_sprite("obstacle.png", (24, 24), OBSTACLE_AMBER)
        
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

    def reset_game(self):
        self.player = Player(self.player_sprite)
        self.npcs = []
        self.obstacles = []
        self.crosswalks =[]
        self.scroll_y = 0
        
        # Spawning Timers
        self.npc_timer = 0
        self.obs_timer = 0
        self.crosswalk_timer = 0
        
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

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            
            if self.state == "START":
                self.draw_start_screen()
            elif self.state == "PLAY":
                self.update_play(dt)
                self.draw_play()
            elif self.state == "GAME_OVER":
                self.draw_game_over()
            
            pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.state == "START" and event.key == pygame.K_RETURN:
                    self.state = "PLAY"
                elif self.state == "GAME_OVER" and event.key == pygame.K_r:
                    self.reset_game()
                    self.state = "PLAY"
                elif self.state == "PLAY":
                    # Indicator Toggles
                    if event.key == pygame.K_q:
                        self.player.blinker = -1 if self.player.blinker != -1 else 0
                    elif event.key == pygame.K_e:
                        self.player.blinker = 1 if self.player.blinker != 1 else 0

    def add_message(self, text, color):
        self.messages.append({"text": text, "color": color, "timer": 2.0})

    def update_play(self, dt):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys, self.joystick)
        
        # Background scroll
        self.scroll_y += self.player.speed * 3 * dt
        if self.scroll_y >= 60:
            self.scroll_y -= 60

        # --- SPAWN LOGIC ---
        self.npc_timer += dt
        if self.npc_timer > max(1.0, 3.0 - (self.player.speed / 100.0)):
            self.npc_timer = 0
            lane = random.choice(LANE_CENTERS)
            npc_speed = random.randint(30, 60)
            self.npcs.append(NPC(lane, -100, npc_speed, self.npc_sprite))

        self.obs_timer += dt
        if self.obs_timer > 8.0:
            self.obs_timer = 0
            lane = random.choice(LANE_CENTERS) + random.randint(-20, 20)
            self.obstacles.append(Obstacle(lane, -100, self.obstacle_sprite))

        self.crosswalk_timer += dt
        if self.crosswalk_timer > 15.0:
            self.crosswalk_timer = 0
            self.crosswalks.append(Crosswalk(-200))

        # --- UPDATE ENTITIES ---
        for npc in self.npcs[:]:
            npc.update(dt, self.player.speed)
            if npc.y > HEIGHT + 100: self.npcs.remove(npc)
        for obs in self.obstacles[:]:
            obs.update(dt, self.player.speed)
            if obs.y > HEIGHT + 100: self.obstacles.remove(obs)
        for cw in self.crosswalks[:]:
            cw.update(dt, self.player.speed)
            if cw.y > HEIGHT + 100: self.crosswalks.remove(cw)

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
                # preserve existing behavior
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
        for cw in self.crosswalks: cw.draw(self.screen)
        for obs in self.obstacles: obs.draw(self.screen)
        for npc in self.npcs: npc.draw(self.screen)
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

    def draw_start_screen(self):
        # Dark themed title screen
        self.screen.fill((18, 18, 20))
        title = self.big_font.render("Safety First", True, PLAYER_COLOR)
        subtitle = self.font.render("2D Driving Simulator :)", True, TEXT)

        # Instruction panel
        panel_w = 600
        panel_h = 220
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 10, 12, 220))
        px = WIDTH//2 - panel_w//2
        py = 220
        self.screen.blit(panel, (px, py))

        instr_lines = [
            "Arrow keys to move lanes — avoid obstacles",
            "Obey red lights — stop at crossings",
            "Q/E to indicate when changing lanes",
        ]

        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))
        self.screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 150))

        ly = py + 16
        for line in instr_lines:
            r = self.font.render(line, True, TEXT)
            self.screen.blit(r, (px + 20, ly))
            ly += 36

        prompt = self.font.render("Press ENTER to Start", True, ACCENT)
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, py + panel_h + 24))

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