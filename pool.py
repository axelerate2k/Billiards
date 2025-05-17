import sys
import os

import pkgutil
import types

if not hasattr(pkgutil, 'ImpImporter'):
    class MockImpImporter:
        def __init__(self, path=None):
            self.path = path
        
        def find_module(self, fullname, path=None):
            return None
    pkgutil.ImpImporter = MockImpImporter
    
    original_find_loader = pkgutil.find_loader
    def patched_find_loader(name, path=None):
        try:
            return original_find_loader(name, path)
        except AttributeError:
            return None, []
    
    pkgutil.find_loader = patched_find_loader

import pygame
import pymunk
import pymunk.pygame_util
import math

pygame.init()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 678
BOTTOM_PANEL = 50

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT + BOTTOM_PANEL))
pygame.display.set_caption("Billiards for Physics 81.1")

space = pymunk.Space()
static_body = space.static_body
draw_options = pymunk.pygame_util.DrawOptions(screen)

clock = pygame.time.Clock()
FPS = 60

lives = 3
dia = 36
pocket_dia = 66
force = 0
max_force = 10000
force_direction = 1
game_running = True
cue_ball_potted = False
taking_shot = True
powering_up = False
potted_balls = []

BG = (50, 50, 50)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)

try:
    font_path = os.path.join("assets", "fonts", "Minecraft.ttf")
    custom_font = pygame.font.Font(font_path, 30)
    custom_large_font = pygame.font.Font(font_path, 60)
    font = custom_font
    large_font = custom_large_font
    print("Custom font loaded successfully!")
except Exception as e:
    print(f"Could not load custom font: {e}")
    print("Falling back to system font...")
    font = pygame.font.SysFont("Lato", 30)
    large_font = pygame.font.SysFont("Lato", 60)

try:
    base_path = os.path.join("assets", "images")

    cue_image = pygame.image.load(os.path.join(base_path, "cue.png")).convert_alpha()
    table_image = pygame.image.load(os.path.join(base_path, "table.png")).convert_alpha()

    ball_images = []
    for i in range(1, 17):
        ball_image = pygame.image.load(os.path.join(base_path, f"ball_{i}.png")).convert_alpha()
        ball_images.append(ball_image)
except pygame.error as e:
    print(f"Error loading images: {e}")
    print("Make sure you're running this from the directory containing the 'assets' folder.")
    print(f"Current directory: {os.getcwd()}")
    sys.exit(1)


def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))

def create_ball(radius, pos):
    body = pymunk.Body()
    body.position = pos
    shape = pymunk.Circle(body, radius)
    shape.mass = 5
    shape.elasticity = 0.8

    pivot = pymunk.PivotJoint(static_body, body, (0, 0), (0, 0))
    pivot.max_bias = 0 # disable joint correction
    pivot.max_force = 1000 # emulate linear friction

    space.add(body, shape, pivot)
    return shape

#setup game balls
balls = []
rows = 5
#potting balls
for col in range(5):
    for row in range(rows):
        pos = (250 + (col * (dia + 1)), BOTTOM_PANEL + 267 + (row * (dia + 1)) + (col * dia / 2))
        new_ball = create_ball(dia / 2, pos)
        balls.append(new_ball)
    rows -= 1
#cue ball
pos = (888, BOTTOM_PANEL + SCREEN_HEIGHT / 2)
cue_ball = create_ball(dia / 2, pos)
balls.append(cue_ball)

#create six pockets on table 
pockets = [
    (55, BOTTOM_PANEL + 63),
    (592, BOTTOM_PANEL + 48),
    (1134, BOTTOM_PANEL + 64),
    (55, BOTTOM_PANEL + 616),
    (592, BOTTOM_PANEL + 629),
    (1134, BOTTOM_PANEL + 616)
]

#create pool table cushions 
cushions = [
    [(88, BOTTOM_PANEL + 56), (109, BOTTOM_PANEL + 77), (555, BOTTOM_PANEL + 77), (564, BOTTOM_PANEL + 56)],
    [(621, BOTTOM_PANEL + 56), (630, BOTTOM_PANEL + 77), (1081, BOTTOM_PANEL + 77), (1102, BOTTOM_PANEL + 56)],
    [(89, BOTTOM_PANEL + 621), (110, BOTTOM_PANEL + 600),(556, BOTTOM_PANEL + 600), (564, BOTTOM_PANEL + 621)],
    [(622, BOTTOM_PANEL + 621), (630, BOTTOM_PANEL + 600), (1081, BOTTOM_PANEL + 600), (1102, BOTTOM_PANEL + 621)],
    [(56, BOTTOM_PANEL + 96), (77, BOTTOM_PANEL + 117), (77, BOTTOM_PANEL + 560), (56, BOTTOM_PANEL + 581)],
    [(1143, BOTTOM_PANEL + 96), (1122, BOTTOM_PANEL + 117), (1122, BOTTOM_PANEL + 560), (1143, BOTTOM_PANEL + 581)]
]

def create_cushion(poly_dims):
    body = pymunk.Body(body_type = pymunk.Body.STATIC)
    body.position = ((0, 0))
    shape = pymunk.Poly(body, poly_dims)
    shape.elasticity = 0.8
    
    space.add(body, shape)

for c in cushions:
    create_cushion(c)

#create pool cue
class Cue():
    def __init__(self, pos):
        self.original_image = cue_image
        self.angle = 0
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.retract_distance = 0  # Amount to retract the cue

    def update(self, angle, retract_distance=0):
        self.angle = angle
        self.retract_distance = retract_distance

    def draw(self, surface):
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        
        # Calculate retraction offset based on cue angle
        retract_x = math.cos(math.radians(self.angle)) * self.retract_distance
        retract_y = -math.sin(math.radians(self.angle)) * self.retract_distance
        
        surface.blit(self.image,
            (self.rect.centerx - self.image.get_width() / 2 + retract_x,
            self.rect.centery - self.image.get_height() / 2 + retract_y)
        )

cue = Cue(balls[-1].body.position)

def get_power_color(force_level):
    # Green for low force (0-33%)
    if force_level < max_force / 3:
        return GREEN
    # Yellow for medium force (33-66%)
    elif force_level < max_force * 2 / 3:
        return YELLOW
    # Red for high force (66-100%)
    else:
        return RED

#game loop
run = True
while run:
    clock.tick(FPS)
    space.step(1 / FPS)

    #fill background
    screen.fill(BG)
    
    #draw top panel
    pygame.draw.rect(screen, BG, (0, 0, SCREEN_WIDTH, BOTTOM_PANEL))
    draw_text("Lives: " + str(lives), font, WHITE, SCREEN_WIDTH - 200, 10)
    draw_text("Potted Balls", font, WHITE, 10, 10)

    #draw potted balls in top panel
    for i, ball in enumerate(potted_balls):
        screen.blit(ball, (180 + (i * 50), 10))
        
    #draw pool table 
    screen.blit(table_image, (0, BOTTOM_PANEL))

    #check if any balls have been potted
    i = 0
    while i < len(balls):
        ball = balls[i]
        potted = False
        for pocket in pockets:
            ball_x_dist = abs(ball.body.position[0] - pocket[0])
            ball_y_dist = abs(ball.body.position[1] - pocket[1])
            ball_dist = math.sqrt((ball_x_dist ** 2) + (ball_y_dist ** 2))
            if ball_dist <= pocket_dia / 2:
                if i == len(balls) - 1:
                    lives -= 1
                    cue_ball_potted = True
                    ball.body.position = (-100, -100)
                    ball.body.velocity = (0.0, 0.0)
                else:
                    space.remove(ball.body)
                    potted_balls.append(ball_images[i])
                    ball_images.pop(i)
                    balls.pop(i)
                    potted = True
                break
        if not potted:
            i += 1

    for i, ball in enumerate(balls):
        screen.blit(ball_images[i], (ball.body.position[0] - ball.radius, ball.body.position[1] - ball.radius))

    taking_shot = True
    for ball in balls:
        if int(ball.body.velocity[0]) != 0 or int(ball.body.velocity[1]) != 0:
            taking_shot = False

    if taking_shot == True and game_running == True:
        if cue_ball_potted == True:
            balls[-1].body.position = (888, BOTTOM_PANEL + SCREEN_HEIGHT / 2)
            cue_ball_potted = False
        mouse_pos = pygame.mouse.get_pos()
        cue.rect.center = balls[-1].body.position
        x_dist = balls[-1].body.position[0] - mouse_pos[0]
        y_dist = -(balls[-1].body.position[1] - mouse_pos[1]) 
        cue_angle = math.degrees(math.atan2(y_dist, x_dist))
        
        retract_distance = 0
        if powering_up:

            retract_distance = min(force / max_force * 50, 50)
            
        cue.update(cue_angle, retract_distance)
        cue.draw(screen)

    #power up pool cue
    if powering_up == True and game_running == True:
        force += 100 * force_direction
        if force >= max_force or force <= 0:
            force_direction *= -1
            
        # Get the appropriate power bar color based on force level
        power_color = get_power_color(force)
        
        # Create a power bar with the current color
        power_bar = pygame.Surface((10, 20))
        power_bar.fill(power_color)
        
        #draw power bars
        for b in range(math.ceil(force / 2000)):
            screen.blit(power_bar,
            (balls[-1].body.position[0] - 30 + (b * 15),
                balls[-1].body.position[1] + 30))
    elif powering_up == False and taking_shot == True and force > 0:
        x_impulse = math.cos(math.radians(cue_angle))
        y_impulse = math.sin(math.radians(cue_angle))
        balls[-1].body.apply_impulse_at_local_point((force * -x_impulse, force * y_impulse), (0, 0))
        force = 0
        force_direction = 1

    #check for game over
    if lives <= 0:
        draw_text("Game Over", large_font, WHITE, SCREEN_WIDTH / 2 - 160, BOTTOM_PANEL + SCREEN_HEIGHT / 2 - 100)
        game_running = False

    if len(balls) == 1:
        draw_text("You Win!", large_font, WHITE, SCREEN_WIDTH / 2 - 160, BOTTOM_PANEL + SCREEN_HEIGHT / 2 - 100)
        game_running = False

    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONDOWN and taking_shot == True:
            powering_up = True
        if event.type == pygame.MOUSEBUTTONUP and taking_shot == True:
            powering_up = False
        if event.type == pygame.QUIT:
            run = False

    
    pygame.display.update()

pygame.quit()