#!/usr/bin/env python3
"""
Eco-Sorter Puzzle
A self-contained educational Pygame puzzle for Ubuntu.
Install dependencies:
  sudo apt update
  sudo apt install python3-pygame
Run the game:
  python3 eco_sorter_puzzle.py
"""

import pygame
import random
import sys
from dataclasses import dataclass

WIDTH = 800
HEIGHT = 600
FPS = 60

PASTEL_BLUE = (178, 224, 255)
LEAF_GREEN = (81, 191, 110)
ELECTRIC_BLUE = (56, 147, 255)
CHARCOAL_GRAY = (56, 63, 69)
SUN_YELLOW = (255, 213, 94)
CORAL_PINK = (255, 134, 139)
WHITE = (255, 255, 255)
SOFT_SHADOW = (20, 20, 35, 40)

ITEM_CATALOG = [
    ("Bottle", "recycle", ELECTRIC_BLUE),
    ("Paper", "recycle", ELECTRIC_BLUE),
    ("Can", "recycle", ELECTRIC_BLUE),
    ("Banana", "compost", LEAF_GREEN),
    ("Leaf", "compost", LEAF_GREEN),
    ("Apple", "compost", LEAF_GREEN),
    ("Wrapper", "trash", CHARCOAL_GRAY),
    ("Chip Bag", "trash", CHARCOAL_GRAY),
    ("Tape", "trash", CHARCOAL_GRAY),
]

BIN_DEFINITIONS = [
    ("Recycle", "recycle", ELECTRIC_BLUE, (80, 420, 200, 160)),
    ("Compost", "compost", LEAF_GREEN, (300, 420, 200, 160)),
    ("Trash", "trash", CHARCOAL_GRAY, (520, 420, 200, 160)),
]

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    color: tuple
    life: float

class ParticleEffect:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color):
        for _ in range(16):
            angle = random.uniform(0, 3.14 * 2)
            speed = random.uniform(120, 260)
            vx = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).x
            vy = speed * pygame.math.Vector2(1, 0).rotate_rad(angle).y
            self.particles.append(
                Particle(
                    x + random.uniform(-10, 10),
                    y + random.uniform(-10, 10),
                    vx,
                    vy,
                    random.uniform(4, 9),
                    color,
                    random.uniform(0.6, 1.2),
                )
            )

    def update(self, dt):
        alive = []
        for particle in self.particles:
            particle.life -= dt
            if particle.life > 0:
                particle.x += particle.vx * dt
                particle.y += particle.vy * dt
                particle.vy += 250 * dt
                particle.radius = max(particle.radius - dt * 3, 1)
                alive.append(particle)
        self.particles = alive

    def draw(self, surface):
        for particle in self.particles:
            alpha = int(max(particle.life * 255, 0))
            color = particle.color + (alpha,)
            radius = int(max(particle.radius, 1))
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, color, (radius, radius), radius)
            surface.blit(surf, (particle.x - radius, particle.y - radius))

class Bin:
    def __init__(self, title, sort_type, color, rect):
        self.title = title
        self.sort_type = sort_type
        self.color = color
        self.rect = pygame.Rect(rect)
        self.icon_color = WHITE

    def draw(self, surface, font):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=24)
        pygame.draw.rect(surface, WHITE, self.rect.inflate(-18, -18), 4, border_radius=20)
        label_surface = font.render(self.title, True, WHITE)
        label_pos = label_surface.get_rect(center=(self.rect.centerx, self.rect.centery + 50))
        surface.blit(label_surface, label_pos)
        self.draw_icon(surface)

    def draw_icon(self, surface):
        icon_center = (self.rect.centerx, self.rect.top + 70)
        if self.sort_type == "recycle":
            for offset in (-22, 0, 22):
                pygame.draw.polygon(
                    surface,
                    self.icon_color,
                    [
                        (icon_center[0] + offset, icon_center[1] - 18),
                        (icon_center[0] + offset + 18, icon_center[1] + 10),
                        (icon_center[0] + offset - 18, icon_center[1] + 10),
                    ],
                )
        elif self.sort_type == "compost":
            pygame.draw.circle(surface, self.icon_color, icon_center, 22, 4)
            pygame.draw.line(surface, self.icon_color, (icon_center[0] - 12, icon_center[1] + 4), (icon_center[0] - 6, icon_center[1] - 12), 4)
            pygame.draw.line(surface, self.icon_color, (icon_center[0] + 12, icon_center[1] + 4), (icon_center[0] + 6, icon_center[1] - 12), 4)
        else:
            pygame.draw.rect(surface, self.icon_color, (*icon_center, 34, 16), border_radius=6)
            pygame.draw.rect(surface, self.icon_color, (icon_center[0] - 28, icon_center[1] - 10, 56, 12), border_radius=6)
            pygame.draw.rect(surface, self.icon_color, (icon_center[0] - 20, icon_center[1] + 10, 40, 10), border_radius=5)

class DraggableItem:
    def __init__(self, label, sort_type, color, initial_position):
        self.label = label
        self.sort_type = sort_type
        self.color = color
        self.width = 140
        self.height = 64
        self.rect = pygame.Rect(initial_position[0], initial_position[1], self.width, self.height)
        self.home_position = pygame.Vector2(self.rect.topleft)
        self.dragging = False
        self.delivered = False
        self.returning = False
        self.velocity = pygame.Vector2(0, 0)
        self.offset = pygame.Vector2(0, 0)
        self.spawn_time = 0

    def update(self, dt):
        if self.delivered:
            return
        if self.dragging:
            return

        if self.returning:
            target = self.home_position
            direction = target - pygame.Vector2(self.rect.topleft)
            self.velocity = direction * 8
            self.rect.x += self.velocity.x * dt
            self.rect.y += self.velocity.y * dt
            if direction.length() < 6:
                self.rect.topleft = self.home_position
                self.returning = False
                self.velocity = pygame.Vector2(0, 0)
            return

        self.velocity.y += 240 * dt
        self.rect.y += self.velocity.y * dt
        floor_y = HEIGHT - 180
        if self.rect.y > floor_y:
            self.rect.y = floor_y
            self.velocity.y *= -0.28
            if abs(self.velocity.y) < 40:
                self.velocity.y = 0

    def draw(self, surface, font):
        shadow = pygame.Surface((self.width + 6, self.height + 6), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 50), shadow.get_rect(), border_radius=18)
        surface.blit(shadow, (self.rect.x + 3, self.rect.y + 3))

        pygame.draw.rect(surface, self.color, self.rect, border_radius=18)
        pygame.draw.rect(surface, WHITE, self.rect, 3, border_radius=18)

        icon_center = (self.rect.x + 28, self.rect.centery)
        pygame.draw.circle(surface, WHITE, icon_center, 16)
        pygame.draw.circle(surface, self.color, icon_center, 12)
        pygame.draw.line(surface, WHITE, (icon_center[0] - 6, icon_center[1] + 4), (icon_center[0] + 6, icon_center[1] + 4), 4)

        label_surface = font.render(self.label, True, WHITE)
        label_pos = label_surface.get_rect(midleft=(self.rect.x + 60, self.rect.centery))
        surface.blit(label_surface, label_pos)

    def start_drag(self, mouse_pos):
        self.dragging = True
        self.returning = False
        self.velocity = pygame.Vector2(0, 0)
        self.offset = pygame.Vector2(mouse_pos) - pygame.Vector2(self.rect.topleft)

    def stop_drag(self):
        self.dragging = False

    def set_position(self, mouse_pos):
        self.rect.topleft = pygame.Vector2(mouse_pos) - self.offset

    def send_home(self):
        self.returning = True
        self.dragging = False

    def is_under_point(self, point):
        return self.rect.collidepoint(point)

    def drop_into_bin(self, bin_area):
        return bin_area.collidepoint(self.rect.center)

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Eco-Sorter Puzzle")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont(None, 56)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)
        self.state = "menu"
        self.bins = [Bin(title, sort_type, color, rect) for title, sort_type, color, rect in BIN_DEFINITIONS]
        self.items = []
        self.particles = ParticleEffect()
        self.score = 0
        self.stars = 0
        self.level = 1
        self.spawn_timer = 0
        self.next_spawn = 0.3
        self.active_item = None
        self.target_score = 15
        self.play_button_rect = pygame.Rect(300, 320, 200, 60)
        self.again_button_rect = pygame.Rect(300, 360, 200, 60)

    def reset_game(self):
        self.items = []
        self.score = 0
        self.stars = 0
        self.level = 1
        self.spawn_timer = 0
        self.next_spawn = 0.3
        self.active_item = None
        self.particles = ParticleEffect()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.state == "menu":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.play_button_rect.collidepoint(event.pos):
                        self.reset_game()
                        self.state = "playing"
            elif self.state == "playing":
                self.handle_play_events(event)
            elif self.state == "victory":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.again_button_rect.collidepoint(event.pos):
                        self.reset_game()
                        self.state = "playing"

    def handle_play_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for item in reversed(self.items):
                if item.is_under_point(event.pos) and not item.delivered:
                    self.active_item = item
                    item.start_drag(event.pos)
                    break
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.active_item is not None:
                placed = False
                for target_bin in self.bins:
                    if self.active_item.drop_into_bin(target_bin.rect):
                        if self.active_item.sort_type == target_bin.sort_type:
                            self.complete_item(self.active_item, target_bin)
                        else:
                            self.active_item.send_home()
                        placed = True
                        break
                if not placed:
                    self.active_item.send_home()
                self.active_item.stop_drag()
                self.active_item = None
        elif event.type == pygame.MOUSEMOTION:
            if self.active_item is not None and self.active_item.dragging:
                self.active_item.set_position(event.pos)

    def complete_item(self, item, bin_area):
        item.delivered = True
        self.score += 1
        self.stars += 1
        self.level = 1 + self.score // 5
        center = item.rect.center
        self.particles.burst(center[0], center[1], SUN_YELLOW)
        self.items.remove(item)
        if self.score >= self.target_score:
            self.state = "victory"

    def spawn_item(self):
        label, sort_type, color = random.choice(ITEM_CATALOG)
        x = random.randint(60, WIDTH - 220)
        y = -random.randint(80, 160)
        item = DraggableItem(label, sort_type, color, (x, y))
        self.items.append(item)

    def update(self, dt):
        if self.state == "playing":
            self.spawn_timer += dt
            if self.spawn_timer >= self.next_spawn and len(self.items) < 5:
                self.spawn_item()
                self.spawn_timer = 0
                self.next_spawn = max(0.25, 0.5 - self.level * 0.03)

            for item in self.items:
                item.update(dt)
            self.particles.update(dt)

    def draw_text(self, text, font, color, center):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=center)
        self.screen.blit(surface, rect)

    def draw(self):
        self.screen.fill(PASTEL_BLUE)
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_playfield()
        elif self.state == "victory":
            self.draw_victory()

    def draw_menu(self):
        self.draw_text("Eco-Sorter Puzzle", self.font_large, CHARCOAL_GRAY, (WIDTH // 2, 140))
        self.draw_text("Help the planet by sorting items into the correct bins!", self.font_medium, CHARCOAL_GRAY, (WIDTH // 2, 200))
        self.draw_button(self.play_button_rect, "Play Game")
        self.draw_text("Use the mouse to drag and drop each treasure.", self.font_small, CHARCOAL_GRAY, (WIDTH // 2, 470))
        self.draw_text("Correct sorts earn stars, wrong bins gently bounce items back.", self.font_small, CHARCOAL_GRAY, (WIDTH // 2, 500))

    def draw_playfield(self):
        self.draw_hud()
        for target_bin in self.bins:
            target_bin.draw(self.screen, self.font_medium)

        for item in self.items:
            item.draw(self.screen, self.font_small)

        self.particles.draw(self.screen)
        self.draw_text("Drag items into the right bins before the day ends!", self.font_small, CHARCOAL_GRAY, (WIDTH // 2, 70))

    def draw_victory(self):
        self.draw_text("Well Done!", self.font_large, CHARCOAL_GRAY, (WIDTH // 2, 150))
        self.draw_text("You sorted eco items like a champion!", self.font_medium, CHARCOAL_GRAY, (WIDTH // 2, 220))
        self.draw_text(f"Score: {self.score}   Level: {self.level}   Stars: {self.stars}", self.font_medium, CHARCOAL_GRAY, (WIDTH // 2, 280))
        self.draw_button(self.again_button_rect, "Play Again")

    def draw_button(self, rect, label):
        mouse_pos = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_pos)
        color = SUN_YELLOW if hovered else CORAL_PINK
        pygame.draw.rect(self.screen, color, rect, border_radius=20)
        pygame.draw.rect(self.screen, WHITE, rect, 4, border_radius=20)
        label_surface = self.font_medium.render(label, True, WHITE)
        label_pos = label_surface.get_rect(center=rect.center)
        self.screen.blit(label_surface, label_pos)

    def draw_hud(self):
        hud_rect = pygame.Rect(0, 0, WIDTH, 100)
        pygame.draw.rect(self.screen, WHITE, hud_rect)
        pygame.draw.rect(self.screen, CHARCOAL_GRAY, hud_rect, 2)
        self.screen.blit(self.font_medium.render(f"Score: {self.score}", True, CHARCOAL_GRAY), (40, 28))
        self.screen.blit(self.font_medium.render(f"Level: {self.level}", True, CHARCOAL_GRAY), (280, 28))
        self.screen.blit(self.font_medium.render(f"Stars: {self.stars}", True, CHARCOAL_GRAY), (520, 28))

if __name__ == "__main__":
    Game().run()
