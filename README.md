# motor-PID

Projet Arduino pour piloter un moteur DC avec encodeur en boucle ouverte et en PID sur Arduino Due, avec un script Python pour logger les mesures série.

## Structure

- `moteurs_PID/moteurs_PID.ino` : PID vitesse pour 1 moteur + 1 encodeur (Arduino Due).
- `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino` : boucle ouverte (Arduino Due).
- `enregistrement/log_moteur.py` : logger serie vers CSV.
- `enregistrement/README.md` : détails du logger.

## Matériel / Câblage

Ce projet est calibré pour un driver DRV8871 en mode XOR et un encodeur 2 voies.

- Encodeur : A sur D2 (INT0), B sur D7.
- Driver DRV8871 en mode XOR : PWM1 sur D9, PWM2 sur D6.

## Carte et port série

- Arduino Due supporte `Serial` (port programmation) et `SerialUSB` (port natif).
- Dans les `.ino`, la variable `USE_SERIAL_USB` permet de choisir le port.
- PWM sur Due est en 12 bits: `PWM_MAX = 4095`.

## Utilisation rapide (PID)

1. Ouvrir l'un des `.ino` dans l'IDE Arduino.
2. Sélectionner la carte Arduino Due et téléverser.
3. Ouvrir le moniteur série à 9600 bauds.
4. Envoyer `h` pour l'aide.
5. (Optionnel) Lancer le logger :

```bash
python3 enregistrement/log_moteur.py
```

## Utilisation rapide (boucle ouverte)

1. Téléverser `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino`.
2. Ouvrir le moniteur série à 9600 bauds.
3. Envoyer `p120` par exemple pour fixer le PWM.
4. Utiliser `s` pour stopper.

## Commandes série (détail)

PID (`moteurs_PID/moteurs_PID.ino`) :

- `h` ou `help` : affiche l'aide.
- `vXXX` : consigne vitesse en RPM (ex: `v120`).
- `s` : stop moteur.
- `kpX`, `kiX`, `kdX` : set gains (ex: `kp0.12`).
- `kp+`, `kp-`, `ki+`, `ki-`, `kd+`, `kd-` : ajuste les gains.
- `g` : affiche Kp/Ki/Kd.

Boucle ouverte (`moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino`) :

- `pXXX` : consigne PWM (0..PWM_MAX).
- `s` : stop moteur.

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

### Commandes de réglage série

```bash
# Afficher les gains actuels
g

# Régler directement les gains
kp0.5    # Kp = 0.5
ki0.01   # Ki = 0.01  
kd0.02   # Kd = 0.02

# Ajustements fins
kp+      # Augmenter Kp de 0.01
kp-      # Diminuer Kp de 0.01
ki+      # Augmenter Ki de 0.001
ki-      # Diminuer Ki de 0.001
kd+      # Augmenter Kd de 0.001
kd-      # Diminuer Kd de 0.001
```

### Points de départ recommandés

Pour un moteur DC avec encodeur :
- **Démarrage** : Kp=0.2, Ki=0.01, Kd=0.005
- **Réponse rapide** : Kp=0.8, Ki=0.05, Kd=0.02
- **Stabilité maximale** : Kp=0.3, Ki=0.02, Kd=0.01

### Conseils pratiques

- Observer la réponse sur le Serial Plotter d'Arduino
- Viser une réponse rapide avec un dépassement < 20%
- Éviter les oscillations continues
- Tester avec différentes charges pour valider la robustesse
- Sauvegarder les gains optimaux dans le code Arduino

## Sorties série attendues

- PID : `rpm:<val> cons:<val>` (pour Serial Plotter).
- Boucle ouverte : `rpm:<val> pwm:<val>` (pour Serial Plotter).

## Logger série

Le script `enregistrement/log_moteur.py` :
- Détecte automatiquement un port série (avec préférence pour Arduino Due).
- Peut enregistrer un CSV quand le firmware envoie `CSV_START` puis `CSV_END`.
- Sinon il affiche simplement les messages série.

Si besoin, forcer le port :

```bash
python3 enregistrement/log_moteur.py --port /dev/ttyACM0 --baud 9600
```

