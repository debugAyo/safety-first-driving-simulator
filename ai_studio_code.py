import os
import pygame
import random
import sys

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
SKY = (148, 184, 212)
ASPHALT = (52, 58, 64)
ROAD_EDGE = (82, 88, 94)
LANE_MARK = (236, 240, 241)
HUD_PANEL = (18, 24, 29)
TEXT = (245, 247, 250)
ACCENT = (224, 172, 80)
DANGER = (196, 58, 58)
SAFE = (79, 149, 87)
PLAYER_BLUE = (32, 92, 155)
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
            pygame.draw.rect(screen, PLAYER_BLUE, self.rect, border_radius=6)

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
            pygame.draw.rect(screen, LANE_MARK, (i, self.y, 20, self.height))
        # Stop line
        pygame.draw.rect(screen, LANE_MARK, self.stop_line)
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

        self.player_sprite = load_sprite("player_car.png", (40, 70), PLAYER_BLUE)
        self.npc_sprite = load_sprite("npc_car.png", (40, 70), NPC_RED)
        self.obstacle_sprite = load_sprite("obstacle.png", (24, 24), OBSTACLE_AMBER)
        
        pygame.joystick.init()
        self.joystick = None
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

        self.state = "START"
        self.reset_game()

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
                if self.state == "START" and event.key == pygame.K_SPACE:
                    self.state = "PLAY"
                elif self.state == "GAME_OVER" and event.key == pygame.K_SPACE:
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
                self.state = "GAME_OVER"
        for obs in self.obstacles:
            if self.player.rect.colliderect(obs.rect):
                self.state = "GAME_OVER"
                
        # Intersection Stop Line (Ran Red Light)
        for cw in self.crosswalks:
            if cw.stop_line.colliderect(self.player.rect) and cw.state == "RED" and not cw.penalized:
                self.safety_score -= 20
                self.infractions["red_light"] += 20
                self.add_message("Ran Red Light! -20", DANGER)
                cw.penalized = True

    def draw_play(self):
        self.screen.fill(SKY)

        pygame.draw.rect(self.screen, ASPHALT, (ROAD_LEFT, 0, ROAD_RIGHT - ROAD_LEFT, HEIGHT))
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_LEFT - 18, 0, 18, HEIGHT))
        pygame.draw.rect(self.screen, ROAD_EDGE, (ROAD_RIGHT, 0, 18, HEIGHT))

        # Draw Road Lines
        pygame.draw.line(self.screen, LANE_MARK, (ROAD_LEFT, 0), (ROAD_LEFT, HEIGHT), 4)
        pygame.draw.line(self.screen, LANE_MARK, (ROAD_RIGHT, 0), (ROAD_RIGHT, HEIGHT), 4)
        
        for div_x in DIVIDERS:
            for y in range(-60, HEIGHT, 60):
                pygame.draw.line(self.screen, LANE_MARK, (div_x, y + self.scroll_y), (div_x, y + self.scroll_y + 30), 2)

        # Draw Entities
        for cw in self.crosswalks: cw.draw(self.screen)
        for obs in self.obstacles: obs.draw(self.screen)
        for npc in self.npcs: npc.draw(self.screen)
        self.player.draw(self.screen)

        self.draw_hud()

    def draw_hud(self):
        # Top-left Score
        score_surf = self.font.render(f"Safety Score: {self.safety_score}", True, TEXT)
        self.screen.blit(score_surf, (10, 10))

        # Bottom-left Current Speed
        speed_surf = self.font.render(f"Speed: {int(self.player.speed)} MPH", True, TEXT)
        self.screen.blit(speed_surf, (10, HEIGHT - 40))

        # Bottom-right Speed Limit
        flash_bg = HUD_PANEL
        if self.player.speed > self.speed_limit and (pygame.time.get_ticks() // 250) % 2 == 0:
            flash_bg = DANGER
            
        limit_rect = pygame.Rect(WIDTH - 120, HEIGHT - 100, 100, 80)
        pygame.draw.rect(self.screen, TEXT, limit_rect)
        pygame.draw.circle(self.screen, flash_bg, limit_rect.center, 35)
        
        limit_text = self.font.render("LIMIT", True, BLACK)
        val_text = self.big_font.render(str(self.speed_limit), True, TEXT)
        self.screen.blit(limit_text, (limit_rect.centerx - limit_text.get_width()//2, limit_rect.top - 25))
        self.screen.blit(val_text, (limit_rect.centerx - val_text.get_width()//2, limit_rect.centery - val_text.get_height()//2))

        # Warnings
        if self.tailgating_active:
            warning_surf = self.big_font.render("TAILGATING WARNING!", True, DANGER)
            self.screen.blit(warning_surf, (WIDTH//2 - warning_surf.get_width()//2, HEIGHT//2 - 100))

        # Floating Messages
        y_offset = 50
        for msg in self.messages:
            msg_surf = self.font.render(msg["text"], True, msg["color"])
            self.screen.blit(msg_surf, (10, y_offset))
            y_offset += 30

    def draw_start_screen(self):
        self.screen.fill(BLACK)
        title = self.big_font.render("Safety First: Driving Simulator", True, PLAYER_BLUE)
        prompt = self.font.render("Press SPACE to Start", True, TEXT)
        
        instr =[
            "Controls:",
            "Up/W : Accelerate   |   Down/S/Space : Brake",
            "Left/A / Right/D : Steer Smoothly",
            "Q : Left Blinker    |   E : Right Blinker",
            "",
            "Rules:",
            "- Stay in your lane (Avoid straddling)",
            "- Indicate (Q/E) when changing lanes",
            "- Follow dynamic speed limits",
            "- Stop at Red Lights",
            "- Overtake NPCs safely on the Left",
            "- Don't tailgate!"
        ]
        
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT - 100))
        
        y = 200
        for line in instr:
            r = self.font.render(line, True, TEXT)
            self.screen.blit(r, (WIDTH//2 - r.get_width()//2, y))
            y += 30

    def draw_game_over(self):
        self.screen.fill(ASPHALT)
        title = self.big_font.render("GAME OVER - CRASHED!", True, DANGER)
        subtitle = self.font.render("SAFETY REPORT", True, ACCENT)
        prompt = self.font.render("Press SPACE to Restart", True, TEXT)
        
        report = [
            f"Base Score: 100",
            f"Lane Straddling Deductions: -{self.infractions['straddling']}",
            f"Failure to Indicate Deductions: -{self.infractions['no_blinker']}",
            f"Tailgating Deductions: -{self.infractions['tailgating']}",
            f"Speeding Deductions: -{self.infractions['speeding']}",
            f"Red Light Violations: -{self.infractions['red_light']}",
            f"Clean Overtake Bonuses: +{self.bonuses['clean_overtake']}",
            "-------------------------------------",
            f"FINAL SAFETY SCORE: {self.safety_score}"
        ]

        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        self.screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, 120))
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT - 60))

        y = 170
        for line in report:
            color = TEXT
            if "FINAL" in line: color = PLAYER_BLUE if self.safety_score > 50 else DANGER
            r = self.font.render(line, True, color)
            self.screen.blit(r, (WIDTH//2 - 200, y))
            y += 35

if __name__ == "__main__":
    game = Game()
    game.run()