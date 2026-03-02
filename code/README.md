# motor-PID

Projet Arduino pour piloter un moteur DC avec encodeur en boucle ouverte et en PID sur Arduino Due, avec un script Python pour logger les mesures serie.

## Structure

- `moteurs_PID/moteurs_PID.ino` : PID vitesse pour 1 moteur + 1 encodeur (Arduino Due).
- `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino` : boucle ouverte (Arduino Due).
- `enregistrement/log_moteur.py` : logger serie vers CSV.
- `enregistrement/README.md` : details du logger.

## Materiel / Cablage

Ce projet est calibre pour un driver DRV8871 en mode XOR et un encodeur 2 voies.

- Encodeur: A sur D2 (INT0), B sur D7.
- Driver DRV8871 en mode XOR: PWM1 sur D9, PWM2 sur D6.

## Carte et port serie

- Arduino Due supporte `Serial` (port programmation) et `SerialUSB` (port natif).
- Dans les `.ino`, la variable `USE_SERIAL_USB` permet de choisir le port.
- PWM sur Due est en 12 bits: `PWM_MAX = 4095`.

## Utilisation rapide (PID)

1. Ouvrir l'un des `.ino` dans l'IDE Arduino.
2. Selectionner la carte Arduino Due et televerser.
3. Ouvrir le moniteur serie a 9600 bauds.
4. Envoyer `h` pour l'aide.
5. (Optionnel) Lancer le logger :

```bash
python3 enregistrement/log_moteur.py
```

## Utilisation rapide (boucle ouverte)

1. Televerser `moteurs_BO/moteurs_open_loop/moteurs_open_loop.ino`.
2. Ouvrir le moniteur serie a 9600 bauds.
3. Envoyer `p120` par exemple pour fixer le PWM.
4. Utiliser `s` pour stopper.

## Commandes serie (detail)

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

## Sorties serie attendues

- PID: `rpm:<val> cons:<val>` (pour Serial Plotter).
- Boucle ouverte: `rpm:<val> pwm:<val>` (pour Serial Plotter).

## Logger serie

Le script `enregistrement/log_moteur.py` :
- Detecte automatiquement un port serie (avec preference pour Arduino Due).
- Peut enregistrer un CSV quand le firmware envoie `CSV_START` puis `CSV_END`.
- Sinon il affiche simplement les messages serie.

Si besoin, forcer le port:

```bash
python3 enregistrement/log_moteur.py --port /dev/ttyACM0 --baud 9600
```

