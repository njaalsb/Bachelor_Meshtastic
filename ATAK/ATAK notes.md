### ATAK notes:

**Offisielle docs:** https://tak.gov/documentation/resources/tak-developers



#### CoT - Cursor-on-Target

* Dette er kommunikasjonsprotokollformatet som ATAK bruker for å dele bl.a possisjonsdata.
* Fungerer som en slags common-language for taktiske systemer, dette er litt som protobufs rolle i meshtastic 
* Oversettelse fra CoT-event til protobuf gjøres i CotEventProcessor.java



**CoT docs:** https://www.mitre.org/sites/default/files/pdf/09\_4937.pdf





**PLUGIN-ID** = 'atak-takdev-plugin'



#### **Versions:**

* JDK 17
* Gradle 8.13
* Kotlin 2.0.21
* Groovy 3.0.22
* ATAK-CIV SDK 5.5.1.8 (But should work with 5.8.0.9)
* Meshtastic 2.7.13



https://www.civtak.org/2020/07/10/sdk-released-civtak-open-sourced/

https://www.ballantyne.online/developing-atak-plugin-101/





## Kommandoer

.\\gradlew build

.\\gradlew --stop

.\\gradlew build --refresh-dependencies

./gradlew assembleCivDebug

.\\gradlew assembleCivDebug --offline (This is the one that is working, wont build otherwise)





## Meshtastic-plugin

**Docs:** 

#### Funksjonalitet

Hovedfunksjonaliteten til pluginnen er i grove trekk:



**Rx**

Meshtastic melding \[protobuf] -> konverteres \[CoT-event] -> sendes til ATAK \[CoT-event] -> markør på ATAK kartet



**Tx**

Melding genereres i ATAK \[CoT-event] -> Plugin gjør om til \[protobuf] -> melding sendes over mesh \[protbuf]

