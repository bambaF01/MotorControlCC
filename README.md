# motor-PID

Projet Arduino pour piloter un moteur DC avec encodeur en boucle ouverte et en PID sur Arduino Due.

## Structure

- `moteurs_PID/moteurs_PID.ino` : PID vitesse pour 1 moteur + 1 encodeur (Arduino Due).
- `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino` : boucle ouverte (Arduino Due).
- `enregistrement/log_moteur.py` : logger vers CSV.
- `enregistrement/README.md` : détails du logger.

## Matériel / Câblage

Ce projet est calibré pour un driver DRV8871 en mode XOR et un encodeur 2 voies.

- Encodeur : A sur D2 (INT0), B sur D7.
- Driver DRV8871 en mode XOR : PWM1 sur D9, PWM2 sur D6.

## Carte et port

- Arduino Due.
- PWM sur Due est en 12 bits: `PWM_MAX = 4095`.

## Utilisation rapide (PID)

1. Ouvrir l'un des `.ino` dans l'IDE Arduino.
2. Sélectionner la carte Arduino Due et téléverser.
3. (Optionnel) Lancer le logger :

```bash
python3 enregistrement/log_moteur.py
```

## Interface utilisateur (UI)

### Fonctionnement de l'application

- L'interface permet de piloter les valeurs (consigne RPM, PWM, gains PID) et d'afficher la courbe en temps reel.
- La courbe affiche la vitesse mesuree et, selon le mode, la consigne.
- Enregistrement CSV local : boutons **Demarrer CSV** / **Arreter CSV** avec fichiers dans `enregistrement/` au format `moteur_YYYYMMDD_HHMMSS.csv`.

## Installation et lancement de l'UI

1. Telecharger ou cloner le projet.
2. Installer Python 3.
3. Installer les dependances Python :

```bash
python3 -m pip install -r enregistrement/requirements.txt
```

4. Si l'UI ne demarre pas (Tkinter manquant), installer :
Linux (Debian/Ubuntu) : `sudo apt install python3-tk`
macOS (Homebrew) : `brew install python-tk`

5. Lancer l'application :

```bash
python3 enregistrement/ui_moteur.py
```

6. Si besoin, forcer le port :

```bash
python3 enregistrement/ui_moteur.py --port /dev/ttyACM0 --baud 9600
```

Notes :
- Windows : utiliser `python` au lieu de `python3` si besoin.

## Utilisation rapide (boucle ouverte)

1. Téléverser `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino`.
2. Lancer l'exemple et verifier le comportement moteur.

## Commandes

Les commandes de controle sont disponibles directement dans l'UI.

## Concepts théoriques

### Boucle Ouverte (Open Loop)

En boucle ouverte, le moteur est commandé directement par une tension PWM (Pulse Width Modulation) sans retour d'information sur sa vitesse réelle.

**Principe de fonctionnement :**
- On applique une PWM fixe au moteur
- La vitesse du moteur dépend de cette PWM mais aussi des conditions externes (charge, tension d'alimentation, etc.)
- **Inconvénient** : Pas de régulation automatique - si la charge augmente, la vitesse diminue

**Schéma de principe :**
```
PWM fixe → Moteur → Vitesse (non régulée)
```

### PID (Proportionnel-Intégral-Dérivé)

Le PID est un régulateur en boucle fermée qui ajuste automatiquement la PWM pour maintenir une vitesse de consigne.

**Principe de fonctionnement :**
- On définit une vitesse de consigne à atteindre
- Le régulateur mesure la vitesse réelle et calcule l'erreur
- Il ajuste la PWM en fonction de cette erreur avec 3 termes :
  - **P (Proportionnel)** : Réaction immédiate à l'erreur
  - **I (Intégral)** : Élimine l'erreur statique accumulée
  - **D (Dérivé)** : Anticipe les variations futures

**Schéma de principe :**
```
Consigne → [PID] → PWM → Moteur → Vitesse → Mesure → [PID]
               ↑___________________________|
```

**Avantages :**
- Maintient la vitesse malgré les variations de charge
- Réponse rapide et précise
- Stabilité du système

## Configuration du PID

Le régulateur PID nécessite un réglage fin des trois paramètres (gains) pour fonctionner correctement.

### Les paramètres du PID

- **Kp (Gain proportionnel)** :
  - Réagit à l'erreur actuelle
  - **Trop faible** : réponse lente, ne atteint pas la consigne
  - **Trop élevé** : oscillations, dépassement de la consigne
  - **Valeur typique** : 0.1 à 2.0

- **Ki (Gain intégral)** :
  - Accumule l'erreur dans le temps pour éliminer l'erreur statique
  - **Trop faible** : erreur résiduelle permanente
  - **Trop élevé** : oscillations lentes, instabilité
  - **Valeur typique** : 0.001 à 0.1

- **Kd (Gain dérivé)** :
  - Anticipe les futures erreurs basées sur le taux de changement
  - **Trop faible** : réponse trop lente aux changements
  - **Trop élevé** : sensibilité au bruit, instabilité
  - **Valeur typique** : 0.001 à 0.1

### Méthode de réglage (approche manuelle)

1. **Commencer avec Ki = 0 et Kd = 0**
2. **Augmenter Kp progressivement** :
   - Commencer avec Kp = 0.1
   - Augmenter jusqu'à obtenir une réponse rapide mais sans oscillations excessives
3. **Ajouter Ki pour éliminer l'erreur statique** :
   - Commencer avec Ki = 0.001
   - Augmenter progressivement jusqu'à éliminer l'erreur résiduelle
4. **Ajouter Kd pour stabiliser** :
   - Commencer avec Kd = 0.001
   - Augmenter pour réduire les oscillations et améliorer le temps de réponse

### Points de départ recommandés

Pour un moteur DC avec encodeur :
- **Démarrage** : Kp=0.2, Ki=0.01, Kd=0.005
- **Réponse rapide** : Kp=0.8, Ki=0.05, Kd=0.02
- **Stabilité maximale** : Kp=0.3, Ki=0.02, Kd=0.01

### Conseils pratiques

- Observer la réponse sur la courbe de l'UI
- Viser une réponse rapide avec un dépassement < 20%
- Éviter les oscillations continues
- Tester avec différentes charges pour valider la robustesse
- Sauvegarder les gains optimaux dans le code Arduino

## Logger

Le script `enregistrement/log_moteur.py` :
- Peut enregistrer un CSV quand le firmware envoie `CSV_START` puis `CSV_END`.
- Sinon il affiche simplement les messages.

Si besoin, forcer le port :

```bash
python3 enregistrement/log_moteur.py --port /dev/ttyACM0 --baud 9600
```
