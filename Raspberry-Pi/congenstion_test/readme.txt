Utstyr:

-4 meshtastic radioer (radio 1-4)
-1 ruter
-2 dempere


scripts:
-"congestion_test.py" 
    -> Leser melding sendt av "time_sender". Tar tiden fra denne meldingen og subtraherer tiden meldingen ble mottatt for å finne transmisjonstiden til meldingen.

-"congestor.py"
    -> Sender melding med 200 bytes data med et intervall på x sekunder.

-"time_sender.py"
    -> Sender en melding med tiden det er når meldingen blir sendt.


Oppsett:

-Sett radio 1 og 2 ved hverandre, radio 3 og 4 ved hverandre og ruteren imellom, slik at radio 1 og 2 ikke har rekkevidde for å kommunisere med radio 3 og 4, men
ruteren imellom har rekkevidde for å kommunisere med alle 4. Dempere brukes på 3 og 4 (-20dB og -30dB, henholdsvis) for å oppnå dette uten å måtte gå over store
distanser. Radioene er alle på en egen kanal, preset "short fast" er brukt. Ruteren er bare en meshtastic radio med "router"-rolle. De andre har "client mute"-rolle


Metode:

-For denne testen er målet å sjekke tiden det tar å sende melding fra radio 1 til 3 gjennom ruteren (transmisjonstiden) med varierende mengde data som går gjennom ruteren.
Filen "no_congestion.csv" inneholder transmisjonstid når ingen annen data går gjennom ruter. Filen "1sek_congestion.csv" inneholder transmisjonstid når 200 bytes blir sendt
fra radio 2 til 4 hver sekund. Filen "05sek_congestion.csv" er transmisjonstid med 200 bytes hvert 0.5 sek og filen "02sek_congestion.csv" er transmisjonstid med 200 bytes
hvert 0.2 sek.
