# Enregistrement moteur

Script Python pour logger les mesures du moteur (PID ou boucle ouverte) dans un CSV.

## Prérequis

- Python 3
- `pyserial`
- `matplotlib`

```bash
python3 -m pip install -r requirements.txt
```

## Utilisation

Depuis ce dossier :

```bash
python3 log_moteur.py
```

Interface UI (pilotage + courbes) :

```bash
python3 ui_moteur.py
```

Options utiles :

```bash
python3 log_moteur.py --port /dev/ttyACM0 --baud 9600
```

Options utiles (UI) :

```bash
python3 ui_moteur.py --port /dev/ttyACM0 --baud 9600
```

## Fonctionnement de l'UI

- Connexion : saisir le port, cliquer sur **Detecter** puis **Connecter**.
- Mode : l'UI detecte automatiquement si le firmware envoie `rpm:... cons:...` (PID) ou `rpm:... pwm:...` (boucle ouverte).
- Commandes disponibles :
  - **Consigne (rpm)** : envoie `vXXX`
  - **PWM** : envoie `pXXX`
  - **Kp/Ki/Kd** : envoie `kpX`, `kiX`, `kdX` (ou via les boutons +/-)
  - **Stop** : envoie `s`
  - **Lire gains** : envoie `g` et met a jour les champs Kp/Ki/Kd
- Courbe temps reel : affiche `rpm` + consigne/PWM selon le mode detecte.
- Enregistrement CSV local : boutons **Demarrer CSV** / **Arreter CSV** avec fichiers dans ce dossier au format `moteur_YYYYMMDD_HHMMSS.csv`.

## Fonctionnement du logger

- Le script peut enregistrer un CSV lorsque le firmware envoie `CSV_START` puis `CSV_END`.
- Les lignes CSV attendues sont au format `t_ms,rpm,cons` (PID) ou `t_ms,rpm,pwm` (BO).

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

## Fichiers générés

Les fichiers CSV sont enregistrés dans ce dossier avec le préfixe :

```
moteur_YYYYMMDD_HHMMSS.csv
```

## Modes supportés

### Mode PID
- Détecte les messages : `rpm: <val> cons: <val>`
- En-tête CSV : `t_ms,rpm,cons`

### Mode Boucle Ouverte
- Détecte les messages : `rpm: <val> pwm: <val>`
- En-tête CSV : `t_ms,rpm,pwm`
