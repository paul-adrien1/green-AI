'''
import torch
from torchvision import transforms
from PIL import Image
from model_definition import SimpleCNN   # si ton modèle est dans un autre fichier

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

idx_to_class = {
    0: "Cardboard",
    1: "Food Organics",
    2: "Glass",
    3: "Metal",
    4: "Miscellaneous Trash",
    5: "Paper",
    6: "Plastic",
    7: "Textile Trash",
    8: "Vegetation"
}
num_classes =  len(idx_to_class)   # ou valeur fixe

# Charger le modèle
cnn = SimpleCNN(num_classes)
cnn.load_state_dict(torch.load("mon_modele.pth", map_location=device))
cnn.to(device)
cnn.eval()

eval_transform = transforms.Compose([
    transforms.Resize((224,224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225])
])


def predict_image(path):
    img = Image.open(path).convert("RGB")
    x = eval_transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = cnn(x)
        _, pred = torch.max(outputs, 1)
    return idx_to_class[pred.item()]



    # chemin vers une image de test
img_path = r"RealWaste_sand/Glass/Glass_1.jpg"  # adapte au vrai chemin

pred = predict_image(img_path)
print("Classe prédite :", pred)
'''

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import json
import os

# --------------------------
# Device
# --------------------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --------------------------
# Charger les classes
# --------------------------
CLASSES_PATH = os.path.join(os.path.dirname(__file__), "classes.json")
with open(CLASSES_PATH) as f:
    classes = json.load(f)

idx_to_class = {i: c for i, c in enumerate(classes)}
num_classes = len(classes)

# --------------------------
# Construire & charger MobileNetV2
# --------------------------
def load_mobilenet(num_classes, weights_path, device):
    model = models.mobilenet_v2(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)

    state_dict = torch.load(weights_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model

WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "mobilenet_v2_trash.pth")
mobilenet = load_mobilenet(num_classes, WEIGHTS_PATH, device)

# --------------------------
# Transforms d'inférence
# --------------------------
eval_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])

# --------------------------
# Fonction de prédiction
# --------------------------
def predict_image(path):
    img = Image.open(path).convert("RGB")
    x = eval_transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = mobilenet(x)
        _, pred = torch.max(outputs, 1)

    return idx_to_class[pred.item()]

# Petit test manuel

test_img = "RealWaste_sand/Glass/Glass_1.jpg"  # adapte ce chemin
print("Pred :", predict_image(test_img))
