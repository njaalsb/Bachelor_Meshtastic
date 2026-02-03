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




trykk [her](https://www.google.com/search?sca_esv=51db692ab24d98dd&sxsrf=ANbL-n5TVgMXDqKfwmMDcL05OClvLxt-rg:1770143484153&udm=2&fbs=ADc_l-YGrpJMQtvjQ6h14rj-dfIrbPkd_Upq68wJVnEIgo2Pw1mVkZoX1l28d-vL-cINyABHXQ7DZdyge7_RJ1gF82Yv1Ee0wmoK8Vt10FuCinvuxUtVtCUa7g_vwhLbgsbYZay3dIMyS7gRT--PIwgbknn0t-IOW7XEcB8D1ORk99SCkg8z562TnAw4CSq6UL-Pr3dsCuHL&q=stock+photos&sa=X&sqi=2&ved=2ahUKEwil7cus-r2SAxWYGRAIHWRnDYUQtKgLegQIExAB&biw=1536&bih=791&dpr=1.25&aic=0#vhid=C17LWZtL-9ahmM&vssid=mosaic)

<img width="800" height="534" alt="image" src="https://github.com/user-attachments/assets/3f737d81-d93f-40ef-8351-79775f0d70ed" />
