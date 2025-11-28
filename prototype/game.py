import os
import random
import pygame

from model import predict_image  # ta fonction d'inférence


# ==============================
# Config générale
# ==============================

# Taille de la fenêtre
WIDTH, HEIGHT = 1000, 700

# Rectangle "plage" à l'intérieur de la fenêtre
MARGIN = 80
PERIM_RECT = pygame.Rect(MARGIN, MARGIN, WIDTH - 2 * MARGIN, HEIGHT - 2 * MARGIN)

# Vitesse du robot (pixels par frame)
ROBOT_SPEED = 4

# Nombre max de déchets
NUM_TRASH = 4

# Dossier racine du projet (là où se trouve game.py)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dossiers
TRASH_ROOT_DIR = os.path.join(PROJECT_DIR, "RealWaste_sand")
SAND_DIR       = os.path.join(PROJECT_DIR, "Sand")
ROBOT_IMG_PATH = os.path.join(PROJECT_DIR, "robot.png")

# Couleurs utiles
PERIM_COLOR   = (160, 140, 100)
TEXT_BG_COLOR = (0, 0, 0)
TEXT_COLOR    = (255, 255, 255)


# ==============================
# Chargement des assets
# ==============================

def load_sand_background():
    """
    Charge une image de sable depuis le dossier Sand et la redimensionne
    à la taille de la fenêtre.
    """
    if not os.path.isdir(SAND_DIR):
        print(f"[WARN] Dossier Sand introuvable : {SAND_DIR}")
        return None

    sand_files = [
        f for f in os.listdir(SAND_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]
    if not sand_files:
        print(f"[WARN] Aucune image de sable trouvée dans {SAND_DIR}")
        return None

    sand_path = os.path.join(SAND_DIR, sand_files[0])  # on prend la première
    img = pygame.image.load(sand_path).convert()
    img = pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
    print(f"[INFO] Fond sable chargé : {sand_path}")
    return img


def load_robot_image(size: int = 48):
    """
    Charge l'image du robot. Si robot.png n'existe pas, renvoie None
    et on tombera en fallback (rectangle).
    """
    if not os.path.isfile(ROBOT_IMG_PATH):
        print(f"[WARN] Image robot introuvable : {ROBOT_IMG_PATH} -> robot affiché comme un carré.")
        return None

    img = pygame.image.load(ROBOT_IMG_PATH).convert_alpha()
    img = pygame.transform.smoothscale(img, (size, size))
    print(f"[INFO] Image robot chargée : {ROBOT_IMG_PATH}")
    return img


# ==============================
# Classes de jeu
# ==============================

class Robot:
    def __init__(self, rect: pygame.Rect, speed: int, sprite: pygame.Surface | None):
        self.rect = rect
        self.speed = speed
        self.sprite = sprite  # image du robot (ou None si fallback)

    def update(self, keys):
        """
        Déplacement contrôlé par le clavier (flèches).
        Le robot reste confiné dans PERIM_RECT.
        """
        dx, dy = 0, 0
        if keys[pygame.K_LEFT]:
            dx -= self.speed
        if keys[pygame.K_RIGHT]:
            dx += self.speed
        if keys[pygame.K_UP]:
            dy -= self.speed
        if keys[pygame.K_DOWN]:
            dy += self.speed

        # Appliquer le mouvement
        self.rect.x += dx
        self.rect.y += dy

        # Contrainte : le robot reste dans PERIM_RECT
        if self.rect.left < PERIM_RECT.left:
            self.rect.left = PERIM_RECT.left
        if self.rect.right > PERIM_RECT.right:
            self.rect.right = PERIM_RECT.right
        if self.rect.top < PERIM_RECT.top:
            self.rect.top = PERIM_RECT.top
        if self.rect.bottom > PERIM_RECT.bottom:
            self.rect.bottom = PERIM_RECT.bottom

    def draw(self, surface):
        if self.sprite is not None:
            surface.blit(self.sprite, self.rect)
        else:
            # fallback : simple carré bleu si pas d'image robot
            pygame.draw.rect(surface, (0, 100, 255), self.rect)


class Trash:
    def __init__(self, image_path: str, pos: tuple[int, int], size: int = 64):
        self.image_path = image_path
        self.size = size
        # Charge l'image et la redimensionne
        raw_img = pygame.image.load(image_path).convert_alpha()
        self.image = pygame.transform.smoothscale(raw_img, (size, size))

        self.rect = self.image.get_rect()
        self.rect.center = pos

        self.scanned = False            # est-ce que le robot est déjà passé dessus ?
        self.predicted_class = None     # résultat de predict_image

    def draw(self, surface, font: pygame.font.Font):
        surface.blit(self.image, self.rect)

        # Si déjà scanné, on affiche la classe au-dessus
        if self.scanned and self.predicted_class is not None:
            text_surf = font.render(self.predicted_class, True, TEXT_COLOR)
            text_rect = text_surf.get_rect(midbottom=(self.rect.centerx, self.rect.top - 5))
            # fond noir pour lisibilité
            bg_rect = text_rect.inflate(6, 4)
            pygame.draw.rect(surface, TEXT_BG_COLOR, bg_rect)
            surface.blit(text_surf, text_rect)


# ==============================
# Fonctions utilitaires
# ==============================

def load_trash_images(root_dir: str, max_images: int = 20):
    """
    Parcourt RealWaste_sand et renvoie une liste de chemins complets de fichiers images.
    """
    img_paths = []
    if not os.path.isdir(root_dir):
        print(f"[WARN] Dossier {root_dir} introuvable.")
        return []

    for cls_name in os.listdir(root_dir):
        cls_dir = os.path.join(root_dir, cls_name)
        if not os.path.isdir(cls_dir):
            continue
        for fname in os.listdir(cls_dir):
            if fname.lower().endswith((".jpg", ".jpeg", ".png")):
                img_paths.append(os.path.join(cls_dir, fname))

    random.shuffle(img_paths)
    return img_paths[:max_images]


def create_trash_objects(img_paths, num_trash: int):
    """
    Crée num_trash objets Trash avec des positions aléatoires à l'intérieur de PERIM_RECT.
    """
    trash_objects = []
    num_trash = min(num_trash, len(img_paths))

    for i in range(num_trash):
        path = img_paths[i]
        # Position aléatoire dans la "plage", mais pas trop près du bord
        margin_inner = 40
        x = random.randint(PERIM_RECT.left + margin_inner, PERIM_RECT.right - margin_inner)
        y = random.randint(PERIM_RECT.top + margin_inner, PERIM_RECT.bottom - margin_inner)
        trash_objects.append(Trash(path, (x, y), size=64))

    return trash_objects


# ==============================
# Boucle principale du jeu
# ==============================

def main():
    pygame.init()
    pygame.display.set_caption("Robot détecteur de déchets sur la plage")

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 20)
    info_font = pygame.font.SysFont("arial", 18)

    # Fond sable (image)
    sand_bg = load_sand_background()
    if sand_bg is None:
        # fallback : on utilise juste un fond beige si aucune image dispo
        sand_bg = pygame.Surface((WIDTH, HEIGHT))
        sand_bg.fill((194, 178, 128))

    # Image du robot
    robot_sprite = load_robot_image(size=48)

    # Charger quelques images de déchets
    all_img_paths = load_trash_images(TRASH_ROOT_DIR, max_images=20)
    if not all_img_paths:
        print("[ERREUR] Aucun déchet trouvé dans RealWaste_sand. Vérifie TRASH_ROOT_DIR.")
        pygame.quit()
        return

    trash_list = create_trash_objects(all_img_paths, NUM_TRASH)

    # Créer le robot : rectangle ayant la taille du sprite (ou 40x40 par défaut)
    if robot_sprite is not None:
        w, h = robot_sprite.get_width(), robot_sprite.get_height()
    else:
        w, h = 40, 40

    robot_rect = pygame.Rect(0, 0, w, h)
    robot_rect.center = PERIM_RECT.center
    robot = Robot(robot_rect, ROBOT_SPEED, robot_sprite)

    running = True
    last_prediction_text = ""  # dernière prédiction affichée en bas de l'écran

    while running:
        dt = clock.tick(60)  # limiter à 60 fps

        # Gestion des événements
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Appuyer sur ECHAP pour quitter
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        # Récupérer les touches appuyées
        keys = pygame.key.get_pressed()

        # Mise à jour du robot (contrôle clavier)
        robot.update(keys)

        # Collisions robot / déchets
        for trash in trash_list:
            if robot.rect.colliderect(trash.rect):
                if not trash.scanned:
                    # On appelle ton modèle pour prédire
                    try:
                        pred = predict_image(trash.image_path)
                        trash.predicted_class = pred
                        last_prediction_text = f"Déchet détecté : {pred}"
                        print(f"[INFO] Collision avec {os.path.basename(trash.image_path)} -> {pred}")
                    except Exception as e:
                        last_prediction_text = f"Erreur prédiction : {e}"
                        print("[ERREUR] pendant predict_image :", e)

                    trash.scanned = True

        # Dessin
        screen.blit(sand_bg, (0, 0))  # fond sable

        # Dessiner la plage (rectangle périmètre)
        pygame.draw.rect(screen, PERIM_COLOR, PERIM_RECT, width=4)

        # Dessiner les déchets
        for trash in trash_list:
            trash.draw(screen, font)

        # Dessiner le robot
        robot.draw(screen)

        # Afficher une zone d'info en bas
        if last_prediction_text:
            info_surf = info_font.render(last_prediction_text, True, TEXT_COLOR)
            info_rect = info_surf.get_rect(midbottom=(WIDTH // 2, HEIGHT - 10))
            bg_rect = info_rect.inflate(10, 6)
            pygame.draw.rect(screen, TEXT_BG_COLOR, bg_rect)
            screen.blit(info_surf, info_rect)

        # Instructions
        help_text = "Flèches pour déplacer le robot - ESC pour quitter"
        help_surf = info_font.render(help_text, True, (20, 20, 20))
        screen.blit(help_surf, (10, 10))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
