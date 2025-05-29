# test q tables are saved and loaded properly

import os, pickle

models_dir = r"C:\Users\lolam\Documents\comp sci\y3\y3-spr\IntelAgents\Coursework\project\src\agents\learning\models"

for fname in os.listdir(models_dir):
    path = os.path.join(models_dir, fname)
    with open(path, "rb") as f:
        data = pickle.load(f)
    Q = data.get("Q", data)    
    eps = data.get("epsilon", None)
    print(f"{fname}: {len(Q)} states, ε = {eps}")