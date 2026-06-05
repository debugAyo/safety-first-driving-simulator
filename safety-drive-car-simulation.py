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


# ------------------------------
# Driving School Prototype
# ------------------------------
class DrivingVehicle:
    def __init__(self, x, y, angle=0.0):
        self.x = x
        self.y = y
        self.angle = angle  # radians
        self.speed = 0.0
        self.length = 46.0
        self.max_steer = math.radians(30)
        self.steer = 0.0
        self.wheel_spin = 0.0
        self.body_bob = 0.0

    def update(self, dt, accel_input, steer_input):
        # Simple kinematic update
        accel = accel_input * 120.0
        # apply accel
        self.speed += accel * dt
        # damping
        self.speed *= (1.0 - 3.0 * dt)
        # limit speed
        self.speed = max(-40.0, min(80.0, self.speed))

        # steering input in [-1,1]
        self.steer = steer_input * self.max_steer

        # Kinematic bicycle-like turn: change angle proportional to steer and forward speed
        if abs(self.speed) > 0.5:
            turn = (self.speed / self.length) * math.tan(self.steer)
            self.angle += turn * dt

        # motion cues for sprite animation
        self.wheel_spin += self.speed * dt * 10.0
        self.body_bob = 0.8 * math.sin(self.wheel_spin * 0.08)

        # update position
        self.x += math.cos(self.angle) * self.speed * dt
        self.y += math.sin(self.angle) * self.speed * dt


class DrivingSchool:
    LEVELS = [
        {
            "name": "Level 1 - Parallel Parking",
            "task": "parallel_parking",
            "objective": "Park cleanly in the bay and hold still.",
            "rules": [
                "Use low speed only.",
                "Stop fully inside the marked bay.",
                "Hold position for 1.5 seconds.",
            ],
            "pass_mark": 78,
            "thumbnail": "parking",
        },
        {
            "name": "Level 2 - Three-Point Turn",
            "task": "three_point",
            "objective": "Turn around using forward and reverse stages.",
            "rules": [
                "Use reverse carefully.",
                "Complete all three stages in order.",
                "Do not leave the practice lane.",
            ],
            "pass_mark": 75,
            "thumbnail": "turn",
        },
        {
            "name": "Level 3 - Road Rules",
            "task": "road_rules",
            "objective": "Drive through checkpoints while following the rules.",
            "rules": [
                "Stay inside the lane.",
                "Signal before lane changes.",
                "Brake for the stop zone.",
            ],
            "pass_mark": 70,
            "thumbnail": "rules",
        },
    ]

    def __init__(self, game, level_index=0):
        self.game = game
        # arena coordinates (top-left origin)
        self.w = 500
        self.h = 520
        self.x = 20
        self.y = 60
        # vehicle sprite (real image instead of a drawn shape)
        self.vehicle_sprite = game.school_car_sprite or game.player_sprite
        # level / rules data
        self.levels = [dict(level) for level in self.LEVELS]
        self.level_index = max(0, min(level_index, len(self.levels) - 1))
        self.task = self.levels[self.level_index]["task"]
        self.timer = 0.0
        self.score = 100
        self.message = ""
        self.level_message = ""
        self.completed_levels = 0
        self.finished = False
        self.vehicle = None
        self.park_rect = None
        self.tp_forward = None
        self.tp_reverse = None
        self.tp_final = None
        self.tp_stage = 0
        self.park_hold = 0.0
        self.rules_broken = 0
        self.rule_timer = 0.0
        self.off_course_cooldown = 0.0
        self.checkpoints = []
        self.checkpoint_index = 0
        self.current_rules = []
        self.current_objective = ""
        self.last_grade = None
        self.last_grade_notes = ""
        self.last_stars = 0
        self.reverse_distance = 0.0
        self.forward_distance = 0.0
        self.boundary_hits = 0
        self.current_passed = False
        self.pending_result = None
        self._build_level()

    def reset(self):
        self.__init__(self.game, self.level_index)

    def _build_level(self):
        level = self.levels[self.level_index]
        self.task = level["task"]
        self.current_rules = level["rules"]
        self.current_objective = level["objective"]
        self.message = ""
        self.level_message = level["name"]
        self.timer = 0.0
        self.rule_timer = 0.0
        self.rules_broken = 0
        self.off_course_cooldown = 0.0
        self.vehicle = DrivingVehicle(self.x + 120, self.y + self.h - 120, angle=-math.pi/2)
        self.park_hold = 0.0
        self.tp_stage = 0
        self.checkpoint_index = 0
        self.last_grade = None
        self.last_grade_notes = ""
        self.last_stars = 0
        self.reverse_distance = 0.0
        self.forward_distance = 0.0
        self.boundary_hits = 0
        self.current_passed = False
        self.pending_result = None

        if self.task == "parallel_parking":
            # wider bay for clearer visual target (width 140, height 110)
            self.park_rect = pygame.Rect(self.x + 260, self.y + self.h - 130, 140, 110)
            self.tp_forward = None
            self.tp_reverse = None
            self.tp_final = None
            self.checkpoints = []
        elif self.task == "three_point":
            self.park_rect = None
            self.tp_forward = pygame.Rect(self.x + 180, self.y + 80, 120, 80)
            self.tp_reverse = pygame.Rect(self.x + 180, self.y + 220, 120, 80)
            self.tp_final = pygame.Rect(self.x + 180, self.y + 360, 120, 80)
            self.checkpoints = []
        else:
            self.park_rect = None
            self.tp_forward = None
            self.tp_reverse = None
            self.tp_final = None
            # road rules checkpoints: simple lane/stop practice path
            self.checkpoints = [
                pygame.Rect(self.x + 100, self.y + 110, 120, 60),
                pygame.Rect(self.x + 220, self.y + 220, 120, 60),
                pygame.Rect(self.x + 320, self.y + 330, 120, 60),
            ]

    def _vehicle_rect(self):
        vpos = pygame.Rect(0, 0, 44, 24)
        vpos.center = (int(self.vehicle.x), int(self.vehicle.y))
        return vpos

    def _render_vehicle_sprite(self):
        base = self.vehicle_sprite
        if base is None:
            w = 40
            h = 20
            base = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(base, PLAYER_COLOR, (0, 0, w, h), border_radius=4)

        car = base.copy()
        wheel_positions = [(10, 58), (30, 58)]
        for wx, wy in wheel_positions:
            pygame.draw.circle(car, (25, 25, 25), (wx, wy), 5)
            pygame.draw.circle(car, (95, 95, 95), (wx, wy), 4, 1)
            spin_angle = self.vehicle.wheel_spin
            px = wx + math.cos(spin_angle) * 4
            py = wy + math.sin(spin_angle) * 4
            pygame.draw.line(car, (220, 220, 220), (wx, wy), (px, py), 1)
            pygame.draw.line(car, (220, 220, 220), (wx, wy), (wx - math.cos(spin_angle) * 4, wy - math.sin(spin_angle) * 4), 1)

        if self.vehicle.speed > 0.5:
            pygame.draw.polygon(car, (255, 255, 255, 120), [(8, 22), (14, 18), (14, 26)])
        elif self.vehicle.speed < -0.5:
            pygame.draw.polygon(car, (255, 255, 255, 120), [(32, 22), (26, 18), (26, 26)])

        tilt = math.degrees(self.vehicle.angle) * -1
        if self.vehicle.steer != 0:
            tilt += max(-6, min(6, math.degrees(self.vehicle.steer) * 0.18))
        rotated = pygame.transform.rotozoom(car, tilt, 1.0)
        return rotated

    def _record_motion(self, dt):
        distance = abs(self.vehicle.speed) * dt
        if self.vehicle.speed >= 0:
            self.forward_distance += distance
        else:
            self.reverse_distance += distance

    def _grade_parallel_parking(self):
        angle_error_deg = abs(math.degrees(wrap_angle(self.vehicle.angle + math.pi / 2)))
        center_error = math.hypot(self.vehicle.x - self.park_rect.centerx, self.vehicle.y - self.park_rect.centery)
        reverse_shortfall = max(0.0, 20.0 - self.reverse_distance)
        score = 100.0
        score -= angle_error_deg * 2.5
        score -= center_error * 0.8
        score -= self.boundary_hits * 20.0
        score -= reverse_shortfall * 2.0
        score -= max(0.0, self.forward_distance - self.reverse_distance) * 0.8
        grade = max(0, min(100, int(score)))
        notes = f"Angle {angle_error_deg:.1f}°, center {center_error:.1f}px, reverse {self.reverse_distance:.1f}"
        return grade, notes, angle_error_deg, center_error

    def _grade_three_point(self):
        reversal_bonus = min(1.0, self.reverse_distance / 18.0)
        score = 100.0
        score -= self.boundary_hits * 15.0
        score -= max(0.0, 12.0 - self.reverse_distance) * 2.0
        score -= max(0.0, self.forward_distance - self.reverse_distance) * 0.5
        score += reversal_bonus * 10.0
        grade = max(0, min(100, int(score)))
        notes = f"Reverse {self.reverse_distance:.1f}, forward {self.forward_distance:.1f}"
        return grade, notes

    def _grade_road_rules(self):
        score = 100.0
        score -= self.boundary_hits * 12.0
        score -= self.rules_broken * 10.0
        score -= max(0.0, 8.0 - self.reverse_distance) * 1.5
        grade = max(0, min(100, int(score)))
        notes = f"Rules broken {self.rules_broken}, off-course {self.boundary_hits}"
        return grade, notes

    def _complete_level(self, grade, notes):
        self.last_grade = grade
        self.last_grade_notes = notes
        self.last_stars = self.grade_to_stars(grade)
        self.score += grade
        pass_mark = self.levels[self.level_index].get("pass_mark", 70)
        if grade >= pass_mark:
            self.current_passed = True
            self.message = f"Level passed: {grade}/100"
            next_level_index = self.level_index + 1 if self.level_index + 1 < len(self.levels) else None
            self.pending_result = {
                "level_name": self.levels[self.level_index]["name"],
                "passed": True,
                "grade": grade,
                "stars": self.last_stars,
                "notes": notes,
                "next_level_index": next_level_index,
                "level_index": self.level_index,
                "finished": next_level_index is None,
            }
        else:
            self.current_passed = False
            self.message = f"Grade {grade}/100 below pass mark {pass_mark}"
            self.pending_result = {
                "level_name": self.levels[self.level_index]["name"],
                "passed": False,
                "grade": grade,
                "stars": self.last_stars,
                "notes": notes,
                "next_level_index": self.level_index,
                "level_index": self.level_index,
                "finished": False,
            }

    def _fail_level(self, reason):
        self.last_grade = 0
        self.last_grade_notes = reason
        self.last_stars = 0
        self.message = reason
        self.score = max(0, self.score - 20)
        self.pending_result = {
            "level_name": self.levels[self.level_index]["name"],
            "passed": False,
            "grade": 0,
            "stars": 0,
            "notes": reason,
            "next_level_index": self.level_index,
            "level_index": self.level_index,
            "finished": False,
        }

    def next_level(self):
        self.completed_levels += 1
        self.score += 60
        if self.level_index + 1 < len(self.levels):
            self.level_index += 1
            self._build_level()
            self.level_message = f"Unlocked: {self.levels[self.level_index]['name']}"
        else:
            self.finished = True
            self.level_message = "All driving school levels complete!"
            self.message = "Driving School Passed!"

    @staticmethod
    def grade_to_stars(grade):
        if grade >= 90:
            return 3
        if grade >= 75:
            return 2
        if grade >= 60:
            return 1
        return 0

    def update(self, dt):
        if self.finished:
            return
        keys = pygame.key.get_pressed()
        # controls: W accelerate, S reverse, A/D steer
        accel = 0.0
        steer = 0.0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            accel = 1.0
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            accel = -1.0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            steer = -1.0
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            steer = 1.0

        self.vehicle.update(dt, accel, steer)
        self._record_motion(dt)
        self.timer += dt
        self.rule_timer += dt
        if self.off_course_cooldown > 0.0:
            self.off_course_cooldown = max(0.0, self.off_course_cooldown - dt)

        # simple collision with arena bounds
        if not (self.x + 8 < self.vehicle.x < self.x + self.w - 8 and self.y + 8 < self.vehicle.y < self.y + self.h - 8):
            self.score -= int(10 * dt)
            self.message = "Off course! Get back inside."
            if self.off_course_cooldown <= 0.0:
                self.rules_broken += 1
                self.boundary_hits += 1
                self.off_course_cooldown = 0.35
        else:
            self.message = ""

        # basic rule reminder / enforcement
        if self.task == "road_rules" and self.rule_timer > 4.0:
            self.rule_timer = 0.0
            self.message = "Remember: signal before changing lanes."

        # Task checks
        if self.task == "parallel_parking":
            # require the car center to be in the bay and the car to be nearly still
            parked_center = self.park_rect.inflate(-12, -12)
            if parked_center.collidepoint(self.vehicle.x, self.vehicle.y) and abs(self.vehicle.speed) < 3.5:
                self.park_hold += dt
            else:
                self.park_hold = 0.0
            if self.park_hold > 1.5:
                grade, notes, angle_error_deg, center_error = self._grade_parallel_parking()
                if self.reverse_distance < 12.0:
                    self._fail_level("Use reverse more accurately before finishing.")
                elif angle_error_deg > 14.0:
                    self._fail_level("Parking angle is too wide. Straighten the car.")
                elif center_error > 20.0:
                    self._fail_level("Not centered enough in the bay.")
                else:
                    self._complete_level(grade, notes)
        elif self.task == "three_point":
            vpos = self._vehicle_rect()
            if self.tp_stage == 0 and self.tp_forward.colliderect(vpos):
                self.tp_stage = 1
                self.message = "Stage 1 complete: Reverse into gap"
            elif self.tp_stage == 1 and self.tp_reverse.colliderect(vpos) and self.vehicle.speed < 1.0:
                self.tp_stage = 2
                self.message = "Stage 2 complete: Finish forward"
            elif self.tp_stage == 2 and self.tp_final.colliderect(vpos):
                grade, notes = self._grade_three_point()
                if self.reverse_distance < 10.0:
                    self._fail_level("Use a cleaner reverse during the turn.")
                else:
                    self._complete_level(grade, notes)
        elif self.task == "road_rules":
            if self.checkpoints and self.checkpoint_index < len(self.checkpoints):
                vpos = self._vehicle_rect()
                if self.checkpoints[self.checkpoint_index].colliderect(vpos):
                    self.checkpoint_index += 1
                    self.score += 40
                    self.message = f"Checkpoint {self.checkpoint_index} passed"
                    if self.checkpoint_index >= len(self.checkpoints):
                        grade, notes = self._grade_road_rules()
                        self._complete_level(grade, notes)

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
        self.school_car_sprite = load_sprite("player_car.png", (40, 70), PLAYER_COLOR)
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
        self.school_select_index = 0
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
        self.school_select_cards = []
        self.school_select_start_button = None
        self.school_select_back_button = None
        self.school_result = None
        # Ensure the system mouse cursor is visible
        pygame.mouse.set_visible(True)
        # Driving school mode instance
        self.school = None
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
        # clear driving school
        self.school = None
        # clear driving school
        self.school = None

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)

    def step(self, dt):
        self.handle_events()

        if self.state == "START":
            self.draw_start_screen()
        elif self.state == "DRIVING_SCHOOL_SELECT":
            self.draw_driving_school_select()
        elif self.state == "PLAY":
            self.update_play(dt)
            self.draw_play()
        elif self.state == "PAUSE":
            # Render the current play frame but do not update game logic
            self.draw_play()
            self.draw_pause_menu()
        elif self.state == "DRIVING_SCHOOL":
            if self.school is not None:
                self.school.update(dt)
                if self.school.pending_result is not None:
                    self.school_result = self.school.pending_result
                    self.school.pending_result = None
                    self.state = "DRIVING_SCHOOL_RESULTS"
                self.school.draw(self.screen)
        elif self.state == "DRIVING_SCHOOL_RESULTS":
            if self.school is not None:
                self.school.draw(self.screen)
            self.draw_driving_school_results()
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
                elif self.state == "DRIVING_SCHOOL_SELECT" and event.button == 1:
                    mx, my = event.pos
                    card_w = 360
                    card_h = 120
                    gap = 18
                    start_y = 120
                    for i in range(3):
                        x = WIDTH // 2 - card_w // 2
                        y = start_y + i * (card_h + gap)
                        rect = pygame.Rect(x, y, card_w, card_h)
                        if rect.collidepoint(mx, my):
                            self.school_select_index = i
                            break
                    if self.school_select_start_button and self.school_select_start_button.collidepoint(mx, my):
                        self.school = DrivingSchool(self, level_index=self.school_select_index)
                        self.state = "DRIVING_SCHOOL"
                        if self.music_on:
                            self.start_music()
                    elif self.school_select_back_button and self.school_select_back_button.collidepoint(mx, my):
                        self.state = "START"
                elif self.state == "DRIVING_SCHOOL_RESULTS" and event.button == 1:
                    mx, my = event.pos
                    if getattr(self, "school_results_next_button", None) and self.school_results_next_button.collidepoint(mx, my):
                        if self.school_result and self.school_result.get("passed"):
                            next_level_index = self.school_result.get("next_level_index")
                            if next_level_index is not None:
                                self.school = DrivingSchool(self, level_index=next_level_index)
                                self.state = "DRIVING_SCHOOL"
                            else:
                                self.school = None
                                self.state = "DRIVING_SCHOOL_SELECT"
                        else:
                            if self.school_result:
                                self.school = DrivingSchool(self, level_index=self.school_result.get("level_index", 0))
                                self.state = "DRIVING_SCHOOL"
                    elif getattr(self, "school_results_back_button", None) and self.school_results_back_button.collidepoint(mx, my):
                        self.school = None
                        self.state = "DRIVING_SCHOOL_SELECT"

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
                elif self.state == "START" and event.key == pygame.K_d:
                    # Open Driving School level select
                    self.state = "DRIVING_SCHOOL_SELECT"
                elif self.state == "DRIVING_SCHOOL_SELECT":
                    if event.key in (pygame.K_1, pygame.K_KP1, pygame.K_LEFT):
                        self.school_select_index = 0
                    elif event.key in (pygame.K_2, pygame.K_KP2):
                        self.school_select_index = 1
                    elif event.key in (pygame.K_3, pygame.K_KP3, pygame.K_RIGHT):
                        self.school_select_index = 2
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.school = DrivingSchool(self, level_index=self.school_select_index)
                        self.state = "DRIVING_SCHOOL"
                        if self.music_on:
                            self.start_music()
                    elif event.key == pygame.K_ESCAPE:
                        self.state = "START"
                elif self.state == "GAME_OVER" and event.key == pygame.K_r:
                    self.reset_game()
                    self.state = "PLAY"
                    if self.music_on:
                        self.start_music()
                elif self.state == "DRIVING_SCHOOL" and event.key == pygame.K_ESCAPE:
                    # exit driving school
                    self.school = None
                    self.state = "DRIVING_SCHOOL_SELECT"
                elif self.state == "DRIVING_SCHOOL_RESULTS":
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if self.school_result and self.school_result.get("passed"):
                            next_level_index = self.school_result.get("next_level_index")
                            if next_level_index is not None:
                                self.school = DrivingSchool(self, level_index=next_level_index)
                                self.state = "DRIVING_SCHOOL"
                            else:
                                self.school = None
                                self.state = "DRIVING_SCHOOL_SELECT"
                        else:
                            if self.school_result:
                                self.school = DrivingSchool(self, level_index=self.school_result.get("level_index", 0))
                                self.state = "DRIVING_SCHOOL"
                    elif event.key == pygame.K_ESCAPE:
                        self.school = None
                        self.state = "DRIVING_SCHOOL_SELECT"
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

        # Driving School prompt (placed above the main prompt to avoid overlap)
        ds = self.font.render("Press D for Driving School (Level Select)", True, PLAYER_COLOR)
        self.screen.blit(ds, (WIDTH//2 - ds.get_width()//2, py + panel_h - 74))

        prompt = self.font.render("Press ENTER to Start", True, PLAYER_COLOR)
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, py + panel_h - 40))

    def draw_driving_school_select(self):
        # dark background with subtle gradient
        for y in range(HEIGHT):
            shade = 12 + int(18 * (y / HEIGHT))
            self.screen.fill((shade, shade + 2, shade + 4), rect=pygame.Rect(0, y, WIDTH, 1))

        title = self.big_font.render("Driving School", True, TEXT)
        subtitle = self.font.render("Choose a practice level before you start", True, ACCENT)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 24))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 72))

        card_hint_font = pygame.font.SysFont("Arial", 18, bold=True)

        cards = []
        card_w = 360
        card_h = 132
        gap = 18
        start_y = 120
        levels = self.school.levels if self.school else DrivingSchool.LEVELS
        # draw a centered translucent panel behind the cards to keep UI readable
        total_h = len(levels) * card_h + (len(levels) - 1) * gap + 36
        panel_w = card_w + 80
        panel_h = total_h + 48
        panel_x = WIDTH // 2 - panel_w // 2
        panel_y = start_y - 18
        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((18, 18, 20, 232))
        pygame.draw.rect(panel_surf, (80, 80, 90), (0, 0, panel_w, panel_h), 2, border_radius=16)
        self.screen.blit(panel_surf, (panel_x, panel_y))
        for i, level in enumerate(levels):
            x = WIDTH // 2 - card_w // 2
            y = start_y + i * (card_h + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            cards.append(rect)
            selected = i == self.school_select_index
            fill = (30, 32, 38) if not selected else (46, 50, 60)
            pygame.draw.rect(self.screen, fill, rect, border_radius=14)
            pygame.draw.rect(self.screen, ACCENT if selected else (78, 78, 86), rect, 2, border_radius=14)
            name = self.font.render(level["name"], True, TEXT)
            self.screen.blit(name, (rect.x + 14, rect.y + 10))
            hint = card_hint_font.render(f"Press {i + 1} or click", True, PLAYER_COLOR)
            self.screen.blit(hint, (rect.x + 14, rect.y + 38))
            thumb = pygame.Rect(rect.x + 14, rect.y + 42, 96, 64)
            self.draw_level_thumbnail(self.screen, thumb, level.get("thumbnail", "parking"), selected)
            ry = rect.y + 50
            for rule in level["rules"][:2]:
                r = self.font.render(f"- {rule}", True, TEXT)
                self.screen.blit(r, (rect.x + 122, ry))
                ry += 24

        self.school_select_cards = cards

        # action buttons
        start_rect = pygame.Rect(WIDTH // 2 - 150, panel_y + panel_h + 12, 140, 40)
        back_rect = pygame.Rect(WIDTH // 2 + 10, panel_y + panel_h + 12, 140, 40)
        self.school_select_start_button = start_rect
        self.school_select_back_button = back_rect
        for rect, label, selected in [
            (start_rect, "Start", True),
            (back_rect, "Back", False),
        ]:
            fill = (58, 64, 78) if selected else (36, 40, 48)
            pygame.draw.rect(self.screen, fill, rect, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT if selected else (70, 70, 80), rect, 2, border_radius=8)
            label_surf = self.font.render(label, True, TEXT)
            self.screen.blit(label_surf, (rect.centerx - label_surf.get_width() // 2, rect.centery - label_surf.get_height() // 2))

        bottom = self.font.render("Enter/Space to start selected level   Esc to go back", True, TEXT)
        self.screen.blit(bottom, (WIDTH // 2 - bottom.get_width() // 2, panel_y + panel_h + 64))

    def draw_level_thumbnail(self, surf, rect, thumbnail_kind, selected=False):
        bg = (32, 34, 40) if not selected else (46, 50, 60)
        pygame.draw.rect(surf, bg, rect, border_radius=10)
        pygame.draw.rect(surf, ACCENT if selected else (78, 78, 86), rect, 2, border_radius=10)
        if thumbnail_kind == "parking":
            bay = rect.inflate(-18, -18)
            pygame.draw.rect(surf, (84, 84, 84), bay, 2)
            pygame.draw.line(surf, (220, 220, 220), (bay.left + 10, bay.bottom - 8), (bay.right - 10, bay.bottom - 8), 3)
            pygame.draw.rect(surf, (234, 187, 64), (rect.centerx - 9, rect.centery - 11, 18, 26), border_radius=4)
        elif thumbnail_kind == "turn":
            pygame.draw.rect(surf, (60, 60, 70), (rect.x + 10, rect.centery - 7, rect.w - 20, 14), border_radius=6)
            pygame.draw.line(surf, (234, 187, 64), (rect.x + 16, rect.centery + 18), (rect.right - 16, rect.centery - 18), 4)
            pygame.draw.polygon(surf, (234, 187, 64), [(rect.right - 18, rect.centery - 18), (rect.right - 22, rect.centery - 8), (rect.right - 10, rect.centery - 12)])
        else:
            for x in range(rect.x + 12, rect.right - 12, 18):
                pygame.draw.line(surf, (220, 220, 220), (x, rect.y + 10), (x, rect.bottom - 10), 2)
            pygame.draw.rect(surf, (234, 187, 64), (rect.x + 18, rect.centery - 8, rect.w - 36, 16), border_radius=5)

    def draw_star_row(self, surf, x, y, stars, max_stars=3):
        for i in range(max_stars):
            cx = x + i * 34
            color = (255, 208, 80) if i < stars else (80, 80, 90)
            points = []
            outer = 12
            inner = 5
            for p in range(10):
                ang = -math.pi / 2 + p * math.pi / 5
                r = outer if p % 2 == 0 else inner
                points.append((cx + math.cos(ang) * r, y + math.sin(ang) * r))
            pygame.draw.polygon(surf, color, points)

    def draw_driving_school_results(self):
        result = self.school_result or {}
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(WIDTH // 2 - 260, HEIGHT // 2 - 180, 520, 360)
        pygame.draw.rect(self.screen, (18, 20, 26), box, border_radius=14)
        pygame.draw.rect(self.screen, (76, 76, 88), box, 2, border_radius=14)

        title_text = "PASS" if result.get("passed") else "FAIL"
        title_color = SAFE if result.get("passed") else DANGER
        title = self.big_font.render(title_text, True, title_color)
        self.screen.blit(title, (box.centerx - title.get_width() // 2, box.y + 18))

        level_name = self.font.render(result.get("level_name", "Driving School"), True, TEXT)
        self.screen.blit(level_name, (box.centerx - level_name.get_width() // 2, box.y + 78))

        grade = int(result.get("grade", 0))
        grade_text = self.font.render(f"Grade: {grade}/100", True, ACCENT)
        self.screen.blit(grade_text, (box.centerx - grade_text.get_width() // 2, box.y + 116))
        self.draw_star_row(self.screen, box.centerx - 34, box.y + 158, int(result.get("stars", 0)))

        notes = self.font.render(result.get("notes", ""), True, TEXT)
        self.screen.blit(notes, (box.centerx - notes.get_width() // 2, box.y + 196))

        next_label = "Next Level" if result.get("passed") and result.get("next_level_index") is not None else ("Finish" if result.get("passed") else "Retry")
        self.school_results_next_button = pygame.Rect(box.centerx - 140, box.bottom - 78, 130, 42)
        self.school_results_back_button = pygame.Rect(box.centerx + 10, box.bottom - 78, 130, 42)

        for rect, label, active in [
            (self.school_results_next_button, next_label, True),
            (self.school_results_back_button, "Select", False),
        ]:
            pygame.draw.rect(self.screen, (56, 60, 70) if active else (38, 42, 50), rect, border_radius=8)
            pygame.draw.rect(self.screen, ACCENT if active else (76, 76, 88), rect, 2, border_radius=8)
            label_surf = self.font.render(label, True, TEXT)
            self.screen.blit(label_surf, (rect.centerx - label_surf.get_width() // 2, rect.centery - label_surf.get_height() // 2))

        hint = self.font.render("Enter/Space to continue   Esc to select a level", True, TEXT)
        self.screen.blit(hint, (box.centerx - hint.get_width() // 2, box.bottom - 24))

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