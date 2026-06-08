#!/usr/bin/env python3
"""
India Capital Matcher
A self-contained Pygame educational map puzzle for Ubuntu terminal.
Run:
  python3 india_capital_matcher.py
"""

import pygame
import random
import sys
import math

# Window settings
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 768
FPS = 60

# Palette
SKY_TOP = (207, 238, 242)
SKY_BOTTOM = (176, 222, 229)
SEA_COLOR = (88, 169, 202)
MAP_BASE = (84, 151, 111)
MAP_HIGHLIGHT = (106, 184, 133)
MOUNTAIN = (244, 244, 244)
MOUNTAIN_SHADOW = (200, 200, 200)
STATE_FILL = (57, 131, 109)
STATE_BORDER = (44, 102, 90)
STATE_MATCHED = (118, 209, 122)
CAPITAL_CARD = (27, 99, 140)
CAPITAL_ACTIVE = (33, 122, 168)
CAPITAL_TEXT = (255, 255, 255)
HUD_PANEL = (255, 255, 255)
TEXT_COLOR = (22, 34, 51)
ACCENT = (222, 165, 68)
BUTTON_COLOR = (31, 88, 142)
BUTTON_HOVER = (64, 119, 180)
WRONG_GLOW = (248, 114, 108)

LEFT_AREA = pygame.Rect(40, 130, 520, 600)
CARD_AREA = pygame.Rect(584, 130, 400, 600)
HUD_AREA = pygame.Rect(0, 0, WINDOW_WIDTH, 120)

STATE_IDLE = "IDLE"
STATE_DRAGGING = "DRAGGING"
STATE_SNAPPED = "SNAPPED"
RETURNING = "RETURNING"
GAME_PLAYING = "PLAYING"
GAME_VICTORY = "VICTORY"

STATE_NODES = [
    {"state": "Jammu & Kashmir", "capital": "Srinagar"},
    {"state": "Uttar Pradesh", "capital": "Lucknow"},
    {"state": "Bihar", "capital": "Patna"},
    {"state": "West Bengal", "capital": "Kolkata"},
    {"state": "Odisha", "capital": "Bhubaneswar"},
    {"state": "Chhattisgarh", "capital": "Raipur"},
    {"state": "Maharashtra", "capital": "Mumbai"},
    {"state": "Karnataka", "capital": "Bengaluru"},
    {"state": "Tamil Nadu", "capital": "Chennai"},
    {"state": "Kerala", "capital": "Thiruvananthapuram"},
    {"state": "Gujarat", "capital": "Gandhinagar"},
    {"state": "Rajasthan", "capital": "Jaipur"},
]


def lerp(start, end, t):
    return start + (end - start) * t


def format_time(milliseconds):
    total_seconds = milliseconds // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        color = BUTTON_HOVER if self.hovered else BUTTON_COLOR
        pygame.draw.rect(surface, color, self.rect, border_radius=20)
        pygame.draw.rect(surface, ACCENT, self.rect, 3, border_radius=20)
        label = self.font.render(self.text, True, (255, 255, 255))
        surface.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hovered


class Particle:
    def __init__(self, pos, velocity, radius, color, lifetime):
        self.pos = pygame.Vector2(pos)
        self.velocity = pygame.Vector2(velocity)
        self.radius = radius
        self.color = color
        self.lifetime = lifetime

    def update(self, dt):
        self.pos += self.velocity * dt
        self.velocity.y += 140 * dt
        self.lifetime -= dt

    def draw(self, surface):
        if self.lifetime > 0:
            alpha = int(max(0, min(255, self.lifetime * 255)))
            circle_surface = pygame.Surface((int(self.radius * 2 + 4), int(self.radius * 2 + 4)), pygame.SRCALPHA)
            pygame.draw.circle(circle_surface, self.color + (alpha,), (int(self.radius + 2), int(self.radius + 2)), int(self.radius))
            surface.blit(circle_surface, (self.pos.x - self.radius - 2, self.pos.y - self.radius - 2))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color):
        for _ in range(18):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(120, 260)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
            radius = random.uniform(3, 7)
            lifetime = random.uniform(0.6, 1.1)
            self.particles.append(Particle((x, y), velocity, radius, color, lifetime))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.lifetime > 0]
        for particle in self.particles:
            particle.update(dt)

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface)


class StateRegion:
    def __init__(self, info, rect):
        self.state = info["state"]
        self.capital = info["capital"]
        self.rect = pygame.Rect(rect)
        self.matched = False

    def draw(self, surface, font):
        fill = STATE_MATCHED if self.matched else STATE_FILL
        pygame.draw.rect(surface, fill, self.rect, border_radius=18)
        pygame.draw.rect(surface, STATE_BORDER, self.rect, 4, border_radius=18)
        title = font.render(self.state, True, (255, 255, 255) if self.matched else TEXT_COLOR)
        surface.blit(title, title.get_rect(center=(self.rect.centerx, self.rect.top + 28)))
        if self.matched:
            capital_text = font.render(self.capital, True, (255, 255, 255))
            surface.blit(capital_text, capital_text.get_rect(center=(self.rect.centerx, self.rect.centery)))

    def contains(self, point):
        return self.rect.collidepoint(point)


class CapitalCard:
    def __init__(self, rect, capital, target_index):
        self.rect = pygame.Rect(rect)
        self.capital = capital
        self.target_index = target_index
        self.state = STATE_IDLE
        self.home = pygame.Vector2(self.rect.topleft)
        self.offset = pygame.Vector2(0, 0)
        self.return_start = pygame.Vector2(0, 0)
        self.return_target = pygame.Vector2(0, 0)
        self.return_t = 0.0

    def draw(self, surface, font):
        color = CAPITAL_ACTIVE if self.state == STATE_DRAGGING else CAPITAL_CARD
        pygame.draw.rect(surface, color, self.rect, border_radius=18)
        pygame.draw.rect(surface, ACCENT, self.rect, 3, border_radius=18)
        label = font.render(self.capital, True, CAPITAL_TEXT)
        surface.blit(label, label.get_rect(center=self.rect.center))

    def start_drag(self, mouse_pos):
        self.state = STATE_DRAGGING
        self.offset = pygame.Vector2(mouse_pos) - pygame.Vector2(self.rect.topleft)

    def start_return(self):
        self.state = RETURNING
        self.return_start = pygame.Vector2(self.rect.topleft)
        self.return_target = pygame.Vector2(self.home)
        self.return_t = 0.0

    def update(self, dt):
        if self.state == RETURNING:
            self.return_t = min(1.0, self.return_t + dt * 3.5)
            self.rect.topleft = (
                lerp(self.return_start.x, self.return_target.x, self.return_t),
                lerp(self.return_start.y, self.return_target.y, self.return_t),
            )
            if self.return_t >= 1.0:
                self.state = STATE_IDLE

    def reset_position(self):
        self.rect.topleft = self.home
        self.state = STATE_IDLE


class IndiaCapitalMatcher:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("India Capital Matcher")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont(None, 34)
        self.font_medium = pygame.font.SysFont(None, 26)
        self.font_small = pygame.font.SysFont(None, 20)
        self.particles = ParticleSystem()
        self.play_again_button = Button((WINDOW_WIDTH // 2 - 90, WINDOW_HEIGHT - 150, 180, 56), "Play Again", self.font_medium)
        self.reset_game()

    def reset_game(self):
        self.start_time = pygame.time.get_ticks()
        self.finish_time = None
        self.game_mode = GAME_PLAYING
        self.selected_card = None
        self.matched_count = 0
        self.wrong_drops = 0
        self.wrong_flash = 0.0
        self.initialize_map()
        self.make_capital_cards()

    def initialize_map(self):
        self.state_regions = []
        rows = 6
        block_width = LEFT_AREA.width - 40
        block_height = 84
        spacing = 18
        start_y = LEFT_AREA.top + 20

        for idx, info in enumerate(STATE_NODES):
            col = idx // rows
            row = idx % rows
            x = LEFT_AREA.left + 20 + col * (block_width + 20)
            y = start_y + row * (block_height + spacing)
            rect = (x, y, block_width, block_height)
            self.state_regions.append(StateRegion(info, rect))

    def make_capital_cards(self):
        order = list(range(len(STATE_NODES)))
        random.shuffle(order)
        self.capital_cards = []
        cols = 2
        card_width = int((CARD_AREA.width - 60) / cols)
        card_height = 56
        spacing = 18
        start_y = CARD_AREA.top + 60

        for idx, target_index in enumerate(order):
            col = idx % cols
            row = idx // cols
            x = int(CARD_AREA.left + 20 + col * (card_width + 20))
            y = int(start_y + row * (card_height + spacing))
            card = CapitalCard((x, y, card_width, card_height), self.state_regions[target_index].capital, target_index)
            self.capital_cards.append(card)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()
            pygame.display.flip()

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if self.game_mode == GAME_PLAYING:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for card in reversed(self.capital_cards):
                        if card.rect.collidepoint(event.pos) and card.state == STATE_IDLE:
                            self.selected_card = card
                            card.start_drag(event.pos)
                            break

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.selected_card:
                    self.handle_drop(self.selected_card)
                    self.selected_card = None

            elif self.game_mode == GAME_VICTORY:
                self.play_again_button.update(mouse_pos)
                if self.play_again_button.clicked(event):
                    self.reset_game()

    def handle_drop(self, card):
        target = self.state_regions[card.target_index]
        if target.contains(card.rect.center) and not target.matched:
            card.rect.center = target.rect.center
            card.state = STATE_SNAPPED
            target.matched = True
            self.matched_count += 1
            self.particles.burst(target.rect.centerx, target.rect.centery, ACCENT)
            if self.matched_count == len(self.state_regions):
                self.finish_time = pygame.time.get_ticks()
                self.game_mode = GAME_VICTORY
        else:
            card.start_return()
            self.wrong_drops += 1
            self.wrong_flash = 0.45

    def update(self, dt):
        if self.selected_card and self.selected_card.state == STATE_DRAGGING:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.selected_card.rect.topleft = (mouse_x - self.selected_card.offset.x, mouse_y - self.selected_card.offset.y)

        for card in self.capital_cards:
            card.update(dt)

        self.particles.update(dt)
        self.wrong_flash = max(0.0, self.wrong_flash - dt)

    def draw_background(self):
        for y in range(WINDOW_HEIGHT):
            t = y / WINDOW_HEIGHT
            color = (
                int(lerp(SKY_TOP[0], SKY_BOTTOM[0], t)),
                int(lerp(SKY_TOP[1], SKY_BOTTOM[1], t)),
                int(lerp(SKY_TOP[2], SKY_BOTTOM[2], t)),
            )
            pygame.draw.line(self.screen, color, (0, y), (WINDOW_WIDTH, y))

        for i in range(12):
            radius = 90 + i * 18
            alpha = max(0, 70 - i * 4)
            cloud = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
            pygame.draw.circle(cloud, (255, 255, 255, alpha), (radius, radius // 2), radius)
            self.screen.blit(cloud, (60 + i * 18, 160 + i * 10))

    def draw_list_panels(self):
        pygame.draw.rect(self.screen, HUD_PANEL, LEFT_AREA, border_radius=28)
        pygame.draw.rect(self.screen, HUD_PANEL, CARD_AREA, border_radius=28)
        pygame.draw.rect(self.screen, (245, 248, 249), LEFT_AREA, 4, border_radius=28)
        pygame.draw.rect(self.screen, (245, 248, 249), CARD_AREA, 4, border_radius=28)

        left_label = self.font_medium.render("States", True, TEXT_COLOR)
        right_label = self.font_medium.render("Capitals", True, TEXT_COLOR)
        self.screen.blit(left_label, (LEFT_AREA.left + 20, LEFT_AREA.top + 18))
        self.screen.blit(right_label, (CARD_AREA.left + 20, CARD_AREA.top + 18))

    def draw(self):
        self.draw_background()
        self.draw_list_panels()
        pygame.draw.rect(self.screen, HUD_PANEL, HUD_AREA)
        pygame.draw.line(self.screen, ACCENT, (0, HUD_AREA.bottom), (WINDOW_WIDTH, HUD_AREA.bottom), 3)
        self.draw_hud()
        self.draw_state_nodes()
        self.draw_card_area()
        self.particles.draw(self.screen)
        if self.game_mode == GAME_VICTORY:
            self.draw_victory_screen()

    def draw_hud(self):
        pygame.draw.rect(self.screen, HUD_PANEL, HUD_AREA)
        pygame.draw.line(self.screen, ACCENT, (0, HUD_AREA.bottom), (WINDOW_WIDTH, HUD_AREA.bottom), 3)
        title = self.font_large.render("India Capital Matcher", True, TEXT_COLOR)
        self.screen.blit(title, (48, 26))
        subtitle = self.font_medium.render("Drag each capital card to the matching state name.", True, TEXT_COLOR)
        self.screen.blit(subtitle, (48, 64))

        progress = self.font_medium.render(f"Matched: {self.matched_count}/{len(self.state_regions)}", True, TEXT_COLOR)
        timer = self.font_medium.render(f"Elapsed: {self.current_time_text()}", True, TEXT_COLOR)
        self.screen.blit(progress, (WINDOW_WIDTH - 320, 28))
        self.screen.blit(timer, (WINDOW_WIDTH - 320, 62))

    def draw_state_nodes(self):
        for region in self.state_regions:
            region.draw(self.screen, self.font_small)

    def draw_card_area(self):
        label = self.font_medium.render("Capital Cards", True, TEXT_COLOR)
        self.screen.blit(label, (CARD_AREA.left + 20, CARD_AREA.top + 16))
        for card in self.capital_cards:
            card.draw(self.screen, self.font_small)
        if self.wrong_flash > 0:
            glow = pygame.Surface((CARD_AREA.width - 20, 120), pygame.SRCALPHA)
            glow.fill((WRONG_GLOW[0], WRONG_GLOW[1], WRONG_GLOW[2], int(self.wrong_flash * 120)))
            self.screen.blit(glow, (CARD_AREA.left + 10, CARD_AREA.bottom - 140))

    def current_time_text(self):
        end_time = self.finish_time if self.finish_time else pygame.time.get_ticks()
        return format_time(end_time - self.start_time)

    def draw_victory_screen(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 225))
        self.screen.blit(overlay, (0, 0))
        card = pygame.Rect(WINDOW_WIDTH // 2 - 340, WINDOW_HEIGHT // 2 - 220, 680, 380)
        pygame.draw.rect(self.screen, HUD_PANEL, card, border_radius=28)
        pygame.draw.rect(self.screen, ACCENT, card, 5, border_radius=28)

        title = self.font_large.render("Amazing! You matched every capital!", True, ACCENT)
        self.screen.blit(title, title.get_rect(center=(WINDOW_WIDTH // 2, card.top + 64)))

        elapsed = format_time(self.finish_time - self.start_time)
        accuracy = self.compute_accuracy()
        rating = self.performance_rating(accuracy)

        stats = [
            f"Total Time: {elapsed}",
            f"Wrong Drops: {self.wrong_drops}",
            f"Accuracy: {accuracy}%",
            f"Rating: {rating}",
        ]
        for idx, line in enumerate(stats):
            text = self.font_medium.render(line, True, TEXT_COLOR)
            self.screen.blit(text, (card.left + 60, card.top + 140 + idx * 52))

        self.play_again_button.draw(self.screen)

    def compute_accuracy(self):
        attempts = self.matched_count + self.wrong_drops
        if attempts == 0:
            return 100
        return max(0, min(100, int((self.matched_count / attempts) * 100)))

    def performance_rating(self, accuracy):
        if accuracy >= 95:
            return "Map Master"
        if accuracy >= 85:
            return "Capital Star"
        if accuracy >= 70:
            return "Smart Explorer"
        return "Learning Hero"

    def update(self, dt):
        if self.selected_card and self.selected_card.state == STATE_DRAGGING:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            self.selected_card.rect.topleft = (mouse_x - self.selected_card.offset.x, mouse_y - self.selected_card.offset.y)

        for card in self.capital_cards:
            card.update(dt)

        self.particles.update(dt)
        self.wrong_flash = max(0.0, self.wrong_flash - dt)

    def render(self):
        self.draw_background()
        self.draw_list_panels()
        pygame.draw.rect(self.screen, HUD_PANEL, HUD_AREA)
        self.draw_hud()
        self.draw_state_nodes()
        self.draw_card_area()
        self.particles.draw(self.screen)
        if self.game_mode == GAME_VICTORY:
            self.draw_victory_screen()


if __name__ == "__main__":
    IndiaCapitalMatcher().run()
