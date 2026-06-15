import pygame
import math
import random

# The Constants i plan on using
WIDTH = 800
HEIGHT = 600

ROAD_LEFT = 150
ROAD_RIGHT = 650
LANE_WIDTH = (ROAD_RIGHT - ROAD_LEFT ) /3
LANE_CENTER = [ROAD_LEFT + LANE_WIDTH * 0.5, ROAD_LEFT + LANE_WIDTH * 1.5, ROAD_LEFT + LANE_WIDTH * 2.5]
#cOlors
PLAYER_COLOR = (0,153,255)
DANGER = (196,58,58)
ACCENT = (224,172,80)
NPC_RED = (149,57,57)
OBSTACLE_AMBER=(190,130, 54)

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
        # 1. I am using a Mass-Damper System
        mass = 1200.0
        lateral_friction_coeff = 0.7
        gravity = 9.8
        max_lateralforce = mass * gravity * lateral_friction_coeff

        # I need to determing the steering input
        steer_input = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:steer_input = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: steer_input = 1
        applied_force = steer_input * max_lateralforce
        #The Damping Force
        damping_factor = 3998.0
        damping_force = -self.vx * damping_factor
        # Now we all now Netwons Law well :); it is F=ma
        lateral_accel = (applied_force + damping_force)/mass
        # And a lil integration for Velocity as i Am  a Mechatronics Student
        self.vx +=lateral_accel * dt
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
        self.lane = int((self.x - ROAD_LEFT) // LANE_WIDTH)
        self.y = y
        self.speed = speed
        self.passed = False  # Track if player overtook this NPC
        self.rect = pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)
        self.sprite = sprite
        self.crashed = False
        self.crash_timer = 0.0
        

    def update(self, dt, player_speed):
        if self.crashed:
            # Keep wrecks moving with traffic, then clear after timer
            self.y += player_speed * 3 * dt
            self.rect.center = (self.x, self.y)
            self.crash_timer -= dt
            return
        self.y += (player_speed - self.speed) * 3 * dt
        self.rect.center = (self.x, self.y)
    
    def try_lane_change(self, target_lane):
        if target_lane < 0 or target_lane > 2:
            return
        self.lane = target_lane
        self.x = LANE_CENTER[target_lane]
        self.rect.centerx = self.x
   

    def draw(self, screen):
        if self.sprite is not None:
            screen.blit(self.sprite, self.rect)
        else:
            color = DANGER if self.crashed else NPC_RED
            pygame.draw.rect(screen, color, self.rect, border_radius=6)
            if self.crashed:
                # Simple wreckage overlay
                pygame.draw.rect(screen, (30, 30, 30), self.rect.inflate(-8, -20), border_radius=4)
                pygame.draw.line(screen, (80, 80, 80), self.rect.topleft, self.rect.bottomright, 2)
                pygame.draw.line(screen, (80, 80, 80), self.rect.topright, self.rect.bottomleft, 2)
                debris = [
                    (self.rect.left - 6, self.rect.bottom - 4),
                    (self.rect.left + 2, self.rect.bottom + 6),
                    (self.rect.left + 10, self.rect.bottom - 2),
                ]
                pygame.draw.polygon(screen, (60, 60, 60), debris)

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

