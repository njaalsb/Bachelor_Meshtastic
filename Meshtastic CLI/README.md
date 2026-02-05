# Meshtastic CLI

Full brukermanual [her](https://meshtastic.org/docs/software/python/cli/).

For å laste ned:

```bash
pip3 install --upgrade "meshtastic[cli]"
```

## Kommandoer:

```bash
meshtastic --port COM16 --info
```

```bash
meshtastic --port com16 --seriallog
```

```bash
meshtastic --set-canned-message "Bloodclat|Test?|bread taste better than key|6-7|Hungy man thinks of bread"
```

Display noder: 
```bash
meshtastic --nodes
```

### Endring av konfigurasjon

```bash
meshtastic --export-config > example_config.yaml
```

Bruk notepad eller et lignende program til å åpne og redigere filen:

```bash
notepad example_config.yaml
```

Kjør så følgende linje for å laste opp den nye konfigurasjonen:

```bash
meshtastic --configure example_config.yaml
```