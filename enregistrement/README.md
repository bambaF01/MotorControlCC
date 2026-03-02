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
- Il detecte automatiquement le mode de fonctionnement :
  - **PID** : `rpm:<val> cons:<val>`
  - **Boucle ouverte** : `rpm:<val> pwm:<val>`
- Il ecoute les sorties serie et peut enregistrer un CSV lorsque l'Arduino envoie `CSV_START` puis `CSV_END`.
- Les lignes CSV attendues sont au format `t_ms,rpm,cons` (PID) ou `t_ms,rpm,pwm` (BO).

## Fichiers generes

Les fichiers CSV sont enregistres dans ce dossier avec le prefixe :

```
moteur_YYYYMMDD_HHMMSS.csv
```

## Modes supportes

### Mode PID
- Detecte les messages : `rpm: <val> cons: <val>`
- En-tete CSV : `t_ms,rpm,cons`

### Mode Boucle Ouverte
- Detecte les messages : `rpm: <val> pwm: <val>`
- En-tete CSV : `t_ms,rpm,pwm`
