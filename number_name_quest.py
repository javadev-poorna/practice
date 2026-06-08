#!/usr/bin/env python3
"""
Number Name Quest
A self-contained Pygame spelling game for Ubuntu.
Install dependencies:
  sudo apt update
  sudo apt install python3-pygame
Run the game:
  python3 number_name_quest.py
"""

import pygame
import random
import sys
import math
import array

WIDTH = 900
HEIGHT = 600
FPS = 60
TIMER_DURATION = 60.0

BACKGROUND = (252, 244, 224)
BUTTON_PRIMARY = (55, 176, 179)
BUTTON_SECONDARY = (255, 134, 139)
BUTTON_ACTIVE = (149, 101, 171)
TEXT_DARK = (50, 50, 50)
PANEL = (255, 255, 255)
SUCCESS = (98, 200, 113)
ERROR = (242, 85, 119)
SHADOW = (0, 0, 0, 60)

NUMBER_RANGES = [
    ("1 to 20", 1, 20),
    ("21 to 50", 21, 50),
    ("51 to 100", 51, 100),
]
SESSION_LENGTHS = [5, 10, 20]

class Button:
    def __init__(self, rect, label, font, active=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.font = font
        self.active = active

    def draw(self, surface):
        color = BUTTON_ACTIVE if self.active else BUTTON_PRIMARY
        pygame.draw.rect(surface, color, self.rect, border_radius=18)
        pygame.draw.rect(surface, TEXT_DARK, self.rect, 3, border_radius=18)
        text_surface = self.font.render(self.label, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class Particle:
    def __init__(self, position, velocity, radius, color, lifespan):
        self.position = pygame.Vector2(position)
        self.velocity = pygame.Vector2(velocity)
        self.radius = radius
        self.color = color
        self.lifespan = lifespan

    def update(self, dt):
        self.lifespan -= dt
        self.position += self.velocity * dt
        self.velocity.y += 220 * dt
        self.radius = max(self.radius - dt * 3, 1)

    def draw(self, surface):
        alpha = int(max(0, min(255, self.lifespan * 255)))
        if alpha > 0:
            glow = pygame.Surface((self.radius * 2 + 4, self.radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, self.color + (alpha,), (int(self.radius + 2), int(self.radius + 2)), int(self.radius))
            surface.blit(glow, (self.position.x - self.radius - 2, self.position.y - self.radius - 2))

class ParticleEffect:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color):
        for _ in range(18):
            speed = random.uniform(120, 280)
            angle = random.uniform(0, 6.28)
            velocity = pygame.Vector2(speed, 0).rotate_rad(angle)
            radius = random.uniform(4, 8)
            lifespan = random.uniform(0.7, 1.2)
            self.particles.append(Particle((x, y), velocity, radius, color, lifespan))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.lifespan > 0]
        for particle in self.particles:
            particle.update(dt)

    def draw(self, surface):
        for particle in self.particles:
            particle.draw(surface)

def number_to_words(n):
    small = {
        0: "ZERO", 1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE",
        6: "SIX", 7: "SEVEN", 8: "EIGHT", 9: "NINE", 10: "TEN",
        11: "ELEVEN", 12: "TWELVE", 13: "THIRTEEN", 14: "FOURTEEN",
        15: "FIFTEEN", 16: "SIXTEEN", 17: "SEVENTEEN", 18: "EIGHTEEN", 19: "NINETEEN",
    }
    tens = {
        20: "TWENTY", 30: "THIRTY", 40: "FORTY", 50: "FIFTY",
        60: "SIXTY", 70: "SEVENTY", 80: "EIGHTY", 90: "NINETY",
    }
    if n < 20:
        return small[n]
    if n < 100:
        if n in tens:
            return tens[n]
        return tens[n // 10 * 10] + "-" + small[n % 10]
    if n == 100:
        return "ONE HUNDRED"
    return ""

class NumberNameQuestGame:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error:
            pass
        pygame.display.set_caption("Number Name Quest")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.SysFont(None, 52)
        self.font_medium = pygame.font.SysFont(None, 36)
        self.font_small = pygame.font.SysFont(None, 24)
        self.state = "selection"
        self.time_left = TIMER_DURATION
        self.congrats_timer = 0.0
        self.congrats_sound = self.create_tone_sound(880, 0.4)
        self.congratulations_active = False
        self.range_buttons = []
        self.length_buttons = []
        self.start_button = None
        self.play_again_button = None
        self.selected_range = None
        self.selected_length = None
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.correct_inputs = 0
        self.total_inputs = 0
        self.mistakes = 0
        self.flash_timer = 0
        self.flash_color = None
        self.particle_effect = ParticleEffect()
        self.active_word = ""
        self.display_word = ""
        self.missing_positions = []
        self.expected_letters = []
        self.filled_letters = []
        self.next_letter_index = 0
        self.number_value = 0
        self.create_ui()

    def create_ui(self):
        button_width = 220
        button_height = 70
        x_start = 80
        spacing = 240
        y_range = 180
        for index, (label, _, _) in enumerate(NUMBER_RANGES):
            rect = (x_start + index * spacing, y_range, button_width, button_height)
            self.range_buttons.append(Button(rect, label, self.font_medium))

        y_length = 300
        for index, length in enumerate(SESSION_LENGTHS):
            rect = (x_start + index * spacing, y_length, button_width, button_height)
            self.length_buttons.append(Button(rect, str(length), self.font_medium))

        self.start_button = Button((280, 420, 240, 70), "Start", self.font_medium)
        self.play_again_button = Button((280, 420, 240, 70), "Play Again", self.font_medium)

    def create_tone_sound(self, frequency, duration):
        if not pygame.mixer.get_init():
            return None
        sample_rate = 44100
        num_samples = int(round(duration * sample_rate))
        data = array.array('h')
        for i in range(num_samples):
            t = i / sample_rate
            value = int(14000 * math.sin(2 * math.pi * frequency * t) * (1.0 - i / num_samples))
            data.append(value)
        try:
            return pygame.mixer.Sound(buffer=data)
        except Exception:
            return None

    def reset_session(self):
        self.questions = []
        self.current_index = 0
        self.score = 0
        self.correct_inputs = 0
        self.total_inputs = 0
        self.mistakes = 0
        self.flash_timer = 0
        self.flash_color = None
        self.particle_effect = ParticleEffect()
        self.active_word = ""
        self.display_word = ""
        self.missing_positions = []
        self.expected_letters = []
        self.filled_letters = []
        self.next_letter_index = 0
        self.number_value = 0
        self.time_left = TIMER_DURATION
        self.congrats_timer = 0.0
        self.congratulations_active = False
        self.finished_message = "Congratulations!"
        self.prepare_questions()
        self.prepare_next_word()

    def prepare_questions(self):
        if self.selected_range is None or self.selected_length is None:
            return
        _, start, end = self.selected_range
        all_numbers = list(range(start, end + 1))
        random.shuffle(all_numbers)
        self.questions = all_numbers[: self.selected_length]

    def prepare_next_word(self):
        if self.current_index >= len(self.questions):
            self.trigger_congratulations("You finished early! Great job!")
            return
        self.number_value = self.questions[self.current_index]
        word = number_to_words(self.number_value)
        self.active_word = word.upper()
        self.display_word, self.missing_positions, self.expected_letters = self.create_puzzle(self.active_word)
        self.filled_letters = ["_"] * len(self.expected_letters)
        self.next_letter_index = 0

    def create_puzzle(self, word):
        letters = [c for c in word]
        candidates = [i for i, c in enumerate(letters) if c.isalpha()]
        remove_count = random.randint(1, min(3, len(candidates)))
        chosen = sorted(random.sample(candidates, remove_count))
        expected = [letters[i] for i in chosen]
        for i in chosen:
            letters[i] = "_"
        return "".join(letters), chosen, expected

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
            if self.state == "selection":
                self.handle_selection_event(event)
            elif self.state == "playing":
                self.handle_play_event(event)
            elif self.state == "score":
                self.handle_score_event(event)

    def handle_selection_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            for index, button in enumerate(self.range_buttons):
                if button.is_clicked(pos):
                    for btn in self.range_buttons:
                        btn.active = False
                    button.active = True
                    self.selected_range = NUMBER_RANGES[index]
            for index, button in enumerate(self.length_buttons):
                if button.is_clicked(pos):
                    for btn in self.length_buttons:
                        btn.active = False
                    button.active = True
                    self.selected_length = SESSION_LENGTHS[index]
            if self.start_button.is_clicked(pos) and self.selected_range and self.selected_length:
                self.reset_session()
                self.state = "playing"

    def handle_play_event(self, event):
        if self.congratulations_active:
            return
        if event.type == pygame.KEYDOWN:
            if self.next_letter_index < len(self.expected_letters):
                char = event.unicode.upper()
                if char and char.isalpha():
                    expected = self.expected_letters[self.next_letter_index]
                    self.total_inputs += 1
                    if char == expected:
                        self.filled_letters[self.next_letter_index] = char
                        self.next_letter_index += 1
                        self.flash_timer = 0.18
                        self.flash_color = SUCCESS
                        self.correct_inputs += 1
                        if self.next_letter_index >= len(self.expected_letters):
                            self.score += 10
                            self.particle_effect.burst(WIDTH // 2, HEIGHT // 2 - 40, SUCCESS)
                            self.current_index += 1
                            self.current_index = min(self.current_index, len(self.questions))
                            pygame.time.set_timer(pygame.USEREVENT + 1, 280, loops=1)
                    else:
                        self.mistakes += 1
                        self.flash_timer = 0.28
                        self.flash_color = ERROR
        elif event.type == pygame.USEREVENT + 1:
            if self.state == "playing":
                self.prepare_next_word()
                pygame.time.set_timer(pygame.USEREVENT + 1, 0)

    def handle_score_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_again_button.is_clicked(event.pos):
                self.selected_range = None
                self.selected_length = None
                for btn in self.range_buttons + self.length_buttons:
                    btn.active = False
                self.state = "selection"

    def update(self, dt):
        if self.state == "playing" and not self.congratulations_active:
            self.time_left = max(0.0, self.time_left - dt)
            if self.time_left <= 0.0:
                self.trigger_congratulations("Time's up! Great effort!")
        self.particle_effect.update(dt)
        if self.flash_timer > 0:
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.flash_color = None
        if self.congratulations_active:
            self.congrats_timer -= dt
            if self.congrats_timer <= 0:
                self.congratulations_active = False
                self.state = "score"

    def draw_text_center(self, text, font, color, y):
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def draw(self):
        self.screen.fill(BACKGROUND)
        if self.state == "selection":
            self.draw_selection_screen()
        elif self.state == "playing":
            self.draw_play_screen()
        elif self.state == "score":
            self.draw_score_screen()

    def draw_panel(self, rect):
        panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (255, 255, 255, 240), panel.get_rect(), border_radius=24)
        pygame.draw.rect(panel, (220, 220, 220, 220), panel.get_rect(), 3, border_radius=24)
        self.screen.blit(panel, rect.topleft)

    def draw_selection_screen(self):
        self.draw_text_center("Number Name Quest", self.font_large, TEXT_DARK, 90)
        self.draw_text_center("Choose a number range and session length", self.font_medium, TEXT_DARK, 140)

        self.draw_panel(pygame.Rect(60, 160, 680, 340))

        for button in self.range_buttons:
            button.draw(self.screen)
        self.draw_text_center("Select range", self.font_small, TEXT_DARK, 160)

        for button in self.length_buttons:
            button.draw(self.screen)
        self.draw_text_center("Session length", self.font_small, TEXT_DARK, 280)

        self.start_button.draw(self.screen)
        if not (self.selected_range and self.selected_length):
            tip = "Choose both options to begin"
            self.draw_text_center(tip, self.font_small, TEXT_DARK, 510)

    def get_puzzle_display(self):
        display_chars = list(self.display_word)
        for i, pos in enumerate(self.missing_positions):
            display_chars[pos] = self.filled_letters[i] if self.filled_letters[i] != "_" else "_"
        return "".join(display_chars)

    def draw_play_screen(self):
        self.draw_panel(pygame.Rect(40, 30, 720, 140))
        title_text = "Fill in the missing letters!"
        self.draw_text_center(title_text, self.font_large, TEXT_DARK, 65)
        status_text = f"Question {self.current_index + 1} of {len(self.questions)}    Score: {self.score}"
        self.draw_text_center(status_text, self.font_small, TEXT_DARK, 110)

        self.draw_panel(pygame.Rect(40, 200, 720, 200))
        number_text = f"{self.number_value} ="
        number_surface = self.font_large.render(number_text, True, BUTTON_SECONDARY)
        self.screen.blit(number_surface, (90, 240))

        puzzle_text = self.get_puzzle_display()
        puzzle_surface = self.font_large.render(puzzle_text, True, TEXT_DARK)
        self.screen.blit(puzzle_surface, (90, 320))

        input_text = "Type missing letters in order"
        self.draw_text_center(input_text, self.font_small, TEXT_DARK, 430)

        timer_text = f"Time left: {int(self.time_left)}s"
        timer_surface = self.font_medium.render(timer_text, True, BUTTON_SECONDARY)
        self.screen.blit(timer_surface, (650, 42))

        feedback_text = f"Correct letters: {self.correct_inputs}   Mistakes: {self.mistakes}"
        self.draw_text_center(feedback_text, self.font_small, TEXT_DARK, 480)

        if self.flash_color:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill(self.flash_color + (60,))
            self.screen.blit(overlay, (0, 0))

        if self.congratulations_active:
            self.draw_congratulations_overlay()

        self.particle_effect.draw(self.screen)

    def draw_score_screen(self):
        self.draw_panel(pygame.Rect(80, 80, 640, 420))
        self.draw_text_center("Well done!", self.font_large, TEXT_DARK, 140)

        accuracy = 100
        if self.total_inputs > 0:
            accuracy = int(max(0, min(100, (self.correct_inputs / self.total_inputs) * 100)))
        star_count = min(5, 1 + self.score // 15)
        ranking = self.get_ranking(star_count, accuracy)

        score_label = f"Total Score: {self.score}"
        accuracy_label = f"Accuracy: {accuracy}%"
        rating_label = f"Ranking: {ranking}"
        stars_label = "Stars: " + "⭐" * star_count

        self.draw_text_center(score_label, self.font_medium, TEXT_DARK, 220)
        self.draw_text_center(accuracy_label, self.font_medium, TEXT_DARK, 270)
        self.draw_text_center(stars_label, self.font_medium, TEXT_DARK, 320)
        self.draw_text_center(rating_label, self.font_medium, TEXT_DARK, 370)

        self.play_again_button.draw(self.screen)

    def get_ranking(self, star_count, accuracy):
        if accuracy >= 95 and star_count >= 4:
            return "Number Wizard!"
        if accuracy >= 85 and star_count >= 3:
            return "Math Explorer"
        if accuracy >= 70:
            return "Letter Learner"
        return "Practice Pal"

    def trigger_congratulations(self, message):
        if self.congratulations_active:
            return
        self.congratulations_active = True
        self.congrats_timer = 2.5
        self.finished_message = message
        self.particle_effect.burst(WIDTH // 2, HEIGHT // 2 - 20, BUTTON_SECONDARY)
        if self.congrats_sound:
            try:
                self.congrats_sound.play()
            except Exception:
                pass

    def draw_congratulations_overlay(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 180))
        self.screen.blit(overlay, (0, 0))
        self.draw_text_center(self.finished_message, self.font_large, BUTTON_SECONDARY, HEIGHT // 2 - 40)
        self.draw_text_center("Fantastic! Your number spelling is shining!", self.font_medium, TEXT_DARK, HEIGHT // 2 + 20)

        pulse = 1.0 + 0.12 * math.sin(pygame.time.get_ticks() * 0.008)
        for offset in range(0, 360, 36):
            radius = int(12 * pulse)
            length = 140 + int(10 * math.sin(math.radians(offset * 2) + pygame.time.get_ticks() * 0.006))
            x = WIDTH // 2 + math.cos(math.radians(offset)) * length
            y = HEIGHT // 2 + math.sin(math.radians(offset)) * length
            pygame.draw.circle(self.screen, BUTTON_PRIMARY, (int(x), int(y)), radius + 6)
            pygame.draw.circle(self.screen, BUTTON_ACTIVE, (int(x), int(y)), radius)

if __name__ == "__main__":
    NumberNameQuestGame().run()
