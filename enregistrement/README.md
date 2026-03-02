# Enregistrement moteur

Script Python pour logger les mesures serie d'un Arduino (PID ou boucle ouverte) dans un CSV.

## Prerequis

- Python 3
- `pyserial` :

```bash
python3 -m pip install pyserial
```

## Utilisation

Depuis ce dossier :

```bash
python3 log_moteur.py
```

Options utiles :

```bash
python3 log_moteur.py --port /dev/ttyACM0 --baud 9600
```

## Fonctionnement

- Le script detecte automatiquement un port serie (avec preference pour l'Arduino Due).
- Il ecoute les sorties serie et peut enregistrer un CSV lorsque l'Arduino envoie `CSV_START` puis `CSV_END`.
- Les lignes CSV attendues sont au format `t_ms,rpm,cons`.

Les messages de type plotter sont aussi reconnus :
- `rpm: <val> cons: <val>` (PID)
- `rpm: <val> pwm: <val>` (boucle ouverte)

## Fichiers generes

Les fichiers CSV sont enregistres dans ce dossier avec le prefixe :

```
moteur_YYYYMMDD_HHMMSS.csv
```
