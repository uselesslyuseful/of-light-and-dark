import pygame
from pygame.locals import *
import random
import asyncio

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
TILE = 30
CHUNK_SIZE = 20
SPAWN_WIDTH = 4
GROUND_Y = 20

PHANTOM_COLOR = (150, 170, 230)

ENEMY_SIZE = 30
ENEMY_SPEED = 1
FLASHLIGHT_RADIUS = 150

BATTERY_MAX = 100.0
BATTERY_DRAIN_PER_SEC = 1
BATTERY_CHARGE_PER_SEC = 0.5

def in_light(world_x, world_y, player_x, player_y, radius=150):
    dx = world_x - player_x
    dy = world_y - player_y
    return dx * dx + dy * dy < radius * radius


def draw_dashed_line(surface, color, start, end, dash_length=6, gap_length=4, width=2):
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    distance = max(abs(dx), abs(dy))

    if distance == 0:
        return

    step = dash_length + gap_length
    steps = int(distance // step) + 1

    for i in range(steps):
        start_frac = (i * step) / distance
        end_frac = min((i * step + dash_length) / distance, 1)

        if start_frac >= 1:
            break

        sx = x1 + dx * start_frac
        sy = y1 + dy * start_frac
        ex = x1 + dx * end_frac
        ey = y1 + dy * end_frac

        pygame.draw.line(surface, color, (sx, sy), (ex, ey), width)


def draw_dashed_rect(surface, color, rect, dash_length=6, gap_length=4, width=2):
    x, y, w, h = rect

    draw_dashed_line(surface, color, (x, y), (x + w, y), dash_length, gap_length, width)
    draw_dashed_line(surface, color, (x, y + h), (x + w, y + h), dash_length, gap_length, width)
    draw_dashed_line(surface, color, (x, y), (x, y + h), dash_length, gap_length, width)
    draw_dashed_line(surface, color, (x + w, y), (x + w, y + h), dash_length, gap_length, width)


class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()

        self.image = pygame.transform.scale(
            pygame.image.load("player.jpg"),
            (30, 30)
        )

        self.world_x = 50.0
        self.world_y = 570.0

        self.vel_x = 0
        self.vel_y = 0

        self.speed = 5
        self.jump_power = -14
        self.gravity = 0.7

        self.on_ground = True

        self.rect = self.image.get_rect()

    def update(self, keys):
        self.vel_x = 0

        if keys[K_LEFT]:
            self.vel_x = -self.speed

        if keys[K_RIGHT]:
            self.vel_x = self.speed

        if keys[K_UP] and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

        self.vel_y += self.gravity

        self.world_x += self.vel_x
        self.world_y += self.vel_y

    def draw(self, screen, camera_x):
        screen.blit(
            self.image,
            (self.world_x - camera_x, self.world_y)
        )


class Enemy:
    def __init__(self, min_x, max_x, world_y, speed=ENEMY_SPEED):
        self.min_x = min_x
        self.max_x = max_x
        self.world_x = (min_x + max_x) / 2
        self.world_y = world_y
        self.speed = speed
        self.direction = random.choice((-1, 1))

    def update(self):
        self.world_x += self.speed * self.direction

        if self.world_x <= self.min_x:
            self.world_x = self.min_x
            self.direction = 1
        elif self.world_x >= self.max_x:
            self.world_x = self.max_x
            self.direction = -1

    def draw(self, screen, camera_x):
        screen_x = self.world_x - camera_x
        screen_y = self.world_y

        center = (int(screen_x + ENEMY_SIZE / 2), int(screen_y + ENEMY_SIZE / 2))
        pygame.draw.circle(screen, (45, 15, 60), center, ENEMY_SIZE // 2)

        eye_y = center[1] - 4
        pygame.draw.circle(screen, (210, 40, 50), (center[0] - 6, eye_y), 3)
        pygame.draw.circle(screen, (210, 40, 50), (center[0] + 6, eye_y), 3)


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 30)

        self.darkness = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self.darkness.fill((0, 0, 0))

        self.flashlight = pygame.Surface((300, 300), pygame.SRCALPHA)
        for radius in range(150, 0, -1):
            alpha = int(255 * radius / 150)
            pygame.draw.circle(
                self.flashlight,
                (0, 0, 0, min(alpha * 1.15, 255)),
                (150, 150),
                radius
            )

        self.left_bound = SCREEN_WIDTH * 0.2
        self.right_bound = SCREEN_WIDTH * 0.8

        self.player = Player()
        self.flashlight_on = True
        self.battery = BATTERY_MAX
        self.highest_world_x = 0

        self.world = []
        self.world_length = 0
        self.camera_x = 0
        self.last_spike_x = None
        self.enemies = []
        self._spawn_world()

    def add_tile(self, x, y, tile_type):
        self.world.append({"x": x, "y": y, "type": tile_type})

    def add_spawn_platform(self):
        for x in range(SPAWN_WIDTH):
            self.add_tile(x, GROUND_Y, "platform")

    def add_enemy(self, min_tile_x, max_tile_x, tile_y):
        min_x = min_tile_x * TILE
        max_x = max_tile_x * TILE
        world_y = tile_y * TILE - ENEMY_SIZE
        self.enemies.append(Enemy(min_x, max_x, world_y))

    def try_place_spike(self, x, y, chance):
        if random.random() >= chance:
            return

        if self.last_spike_x is not None and x - self.last_spike_x == 2:
            return

        self.add_tile(x, y, "spike")
        self.last_spike_x = x

    def generate_chunk(self, start_x):
        x = start_x
        i = 0
        while i < CHUNK_SIZE:
            roll = random.random()

            if roll < 0.05:
                length = random.randint(1, 10)
                height = GROUND_Y - random.randint(2, 5)

                for j in range(length):
                    self.add_tile(x + j, height, "phantom")

                x += length
                i += length
                continue

            elif roll < 0.08:
                width = random.randint(5, 9)

                for j in range(width):
                    self.add_tile(x + j, GROUND_Y, "platform")

                margin = 1
                self.add_enemy(x + margin, x + width - 1 - margin, GROUND_Y)

                x += width
                i += width
                continue

            elif roll < 0.43:
                length = random.randint(1, 10)
                height = GROUND_Y - random.randint(2, 5)

                for j in range(length):
                    self.add_tile(x + j, height, "platform")
                    if j > 0:
                        self.try_place_spike(x + j, height - 1, 0.25)

                x += length
                i += length
                continue

            elif roll < 0.63:
                steps = random.randint(3, 6)

                for j in range(steps):
                    self.add_tile(x + j, GROUND_Y - j, "platform")

                x += steps
                i += steps
                continue

            else:
                self.add_tile(x, GROUND_Y, "platform")
                self.try_place_spike(x, GROUND_Y - 1, 0.1)

            x += 1
            i += 1

        self.world_length = x

    def ensure_generation(self, player_tile_x):
        if self.world_length - player_tile_x < 50:
            self.generate_chunk(self.world_length)

    def _spawn_world(self):
        self.world = []
        self.world_length = 0
        self.camera_x = 0
        self.last_spike_x = None
        self.enemies = []

        self.add_spawn_platform()
        self.world_length = SPAWN_WIDTH
        self.generate_chunk(self.world_length)

    def check_collision(self):
        player = self.player
        player.on_ground = False

        for tile in self.world:
            tile_type = tile["type"]

            if tile_type == "platform":
                solid = True
            elif tile_type == "phantom":
                solid = not self.flashlight_on
            else:
                solid = False

            if not solid:
                continue

            tx = tile["x"] * TILE
            ty = tile["y"] * TILE

            if (
                player.world_x + 30 > tx and
                player.world_x < tx + TILE and
                player.world_y + 30 >= ty and
                player.world_y < ty + TILE and
                player.vel_y >= 0
            ):
                player.world_y = ty - 30
                player.vel_y = 0
                player.on_ground = True

    def check_spikes(self):
        player = self.player
        for tile in self.world:
            if tile["type"] != "spike":
                continue

            tx = tile["x"] * TILE
            ty = tile["y"] * TILE

            if (
                player.world_x < tx + TILE and
                player.world_x + 30 > tx and
                player.world_y < ty + TILE and
                player.world_y + 30 > ty
            ):
                return True

        return False

    def update_enemies(self):
        player = self.player
        still_active = []

        for enemy in self.enemies:
            enemy.update()
            if player.world_x > enemy.max_x + TILE:
                continue

            still_active.append(enemy)

        self.enemies = still_active

    def check_enemy_collision(self):
        player = self.player
        for enemy in self.enemies:
            if (
                player.world_x < enemy.world_x + ENEMY_SIZE and
                player.world_x + 30 > enemy.world_x and
                player.world_y < enemy.world_y + ENEMY_SIZE and
                player.world_y + 30 > enemy.world_y
            ):
                return True

        return False

    def toggle_flashlight(self):
        if not self.flashlight_on and self.battery <= 0:
            return

        self.flashlight_on = not self.flashlight_on

    def update_battery(self, dt):
        if self.flashlight_on:
            self.battery -= BATTERY_DRAIN_PER_SEC * dt

            if self.battery <= 0:
                self.battery = 0
                self.flashlight_on = False
        else:
            self.battery += BATTERY_CHARGE_PER_SEC * dt

            if self.battery > BATTERY_MAX:
                self.battery = BATTERY_MAX

    def reset(self):
        self.player.world_x = 50
        self.player.world_y = 570
        self.player.vel_x = 0
        self.player.vel_y = 0
        self.player.on_ground = True

        self.battery = BATTERY_MAX

        self._spawn_world()

    def update(self, keys, dt):
        self.update_battery(dt)

        self.player.update(keys)
        self.check_collision()
        self.ensure_generation(int(self.player.world_x // TILE))
        self.update_enemies()

        if self.check_spikes() or self.check_enemy_collision() or self.player.world_y > 1500:
            self.reset()
            return

        player_screen_x = self.player.world_x - self.camera_x

        if player_screen_x < self.left_bound:
            self.camera_x -= (self.left_bound - player_screen_x)
        elif player_screen_x > self.right_bound:
            self.camera_x += (player_screen_x - self.right_bound)

        if self.player.world_x - 50 > self.highest_world_x:
            self.highest_world_x = self.player.world_x - 50

    def _draw_tile(self, tile, wx, wy):
        screen_x = wx - self.camera_x
        screen_y = wy

        if tile["type"] == "platform":
            pygame.draw.rect(self.screen, (80, 80, 80), (screen_x, screen_y, TILE, TILE))

        elif tile["type"] == "phantom":
            draw_dashed_rect(self.screen, PHANTOM_COLOR, (screen_x, screen_y, TILE, TILE))

        elif tile["type"] == "spike":
            pygame.draw.polygon(
                self.screen,
                (200, 50, 50),
                [
                    (screen_x, screen_y + TILE),
                    (screen_x + TILE / 2, screen_y),
                    (screen_x + TILE, screen_y + TILE)
                ]
            )

    def draw_world(self):
        px = self.player.world_x
        py = self.player.world_y

        if self.flashlight_on:
            for tile in self.world:
                wx = tile["x"] * TILE
                wy = tile["y"] * TILE

                if not in_light(wx, wy, px, py, 160):
                    continue

                self._draw_tile(tile, wx, wy)
        else:
            player_col = int(px // TILE)
            player_row = int(py // TILE)

            visible_cells = {
                (player_col - 1, player_row),
                (player_col + 1, player_row),
                (player_col, player_row + 1),
                (player_col, player_row - 1),
                (player_col - 1, player_row - 1),
                (player_col + 1, player_row - 1),
                (player_col + 1, player_row + 1),
                (player_col - 1, player_row + 1),
            }

            for tile in self.world:
                if (tile["x"], tile["y"]) not in visible_cells:
                    continue

                wx = tile["x"] * TILE
                wy = tile["y"] * TILE
                self._draw_tile(tile, wx, wy)

    def draw_enemies(self):
        px = self.player.world_x
        py = self.player.world_y

        for enemy in self.enemies:
            cx = enemy.world_x + ENEMY_SIZE / 2
            cy = enemy.world_y + ENEMY_SIZE / 2

            lit = self.flashlight_on and in_light(cx, cy, px, py, FLASHLIGHT_RADIUS)

            if lit:
                continue

            enemy.draw(self.screen, self.camera_x)

    def draw_battery(self):
        x, y = 20, 20
        bar_width, bar_height = 150, 16

        pct = self.battery / BATTERY_MAX
        fill_width = int(bar_width * pct)

        if pct > 0.5:
            fill_color = (80, 200, 100)
        elif pct > 0.2:
            fill_color = (230, 200, 60)
        else:
            fill_color = (220, 60, 60)

        pygame.draw.rect(self.screen, (60, 60, 60), (x, y, bar_width, bar_height))
        if fill_width > 0:
            pygame.draw.rect(self.screen, fill_color, (x, y, fill_width, bar_height))
        pygame.draw.rect(self.screen, (200, 200, 200), (x, y, bar_width, bar_height), 2)

        label = self.font.render(f"{round(self.battery)}%", True, (255, 255, 255))
        self.screen.blit(label, (x + bar_width + 10, y - 3))

    def draw(self):
        self.screen.fill((30, 30, 30))

        px = self.player.world_x - self.camera_x + 15
        py = self.player.world_y + 15
        self.darkness.fill((0, 0, 0, 240))
        if self.flashlight_on:
            self.darkness.blit(
                self.flashlight,
                (px - 150, py - 150),
                special_flags=pygame.BLEND_RGBA_SUB
            )
        self.screen.blit(self.darkness, (0, 0))
        self.player.draw(self.screen, self.camera_x)

        self.draw_world()
        self.draw_enemies()

        score = max(round(self.player.world_x - 50), round(self.highest_world_x))
        score_text = self.font.render("High Score: " + str(score), True, (255, 255, 255))
        score_rect = score_text.get_rect(midtop=(SCREEN_WIDTH // 2, 5))
        self.screen.blit(score_text, score_rect)

        self.draw_battery()

async def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game = Game(screen)

    running = True
    while running:
        dt = game.clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_SPACE:
                    game.toggle_flashlight()

        keys = pygame.key.get_pressed()
        game.update(keys, dt)
        game.draw()

        pygame.display.flip()

        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())