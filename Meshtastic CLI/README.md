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

### Kanaler

Endre disse linjene i config-filen for å bruke 'Meshtastic Norway' sin mest brukte kanal:

```bash
bandwidth: 62
codingRate: 5
hopLimit: 3
overrideFrequency: 869.525
region: EU_868
spreadFactor: 8
```

Ellers kan man endre preset på devicen eller kjøre preset kommandoer:

```bash
--ch-vlongslow        Change to the very long-range and slow modem preset
--ch-longslow         Change to the long-range and slow modem preset
--ch-longfast         Change to the long-range and fast modem preset
--ch-medslow          Change to the med-range and slow modem preset
--ch-medfast          Change to the med-range and fast modem preset
--ch-shortslow        Change to the short-range and slow modem preset
--ch-shortfast        Change to the short-range and fast modem preset
```
