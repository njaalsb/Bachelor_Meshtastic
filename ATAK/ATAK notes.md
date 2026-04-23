### ATAK notes:

Viktige filer

* app/src/main/assets/plugin.xml
* app/src/main/java/com/atakmap/android/meshtastic
* app/src/main/java/com/atakmap/android/meshtastic/plugin/MeshtasticLifecycle.java





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



Paths:

atak.sdk=C\\:\\\\ATAK-CIV-5.5.1.8-SDK

takdev.plugin=C\\:\\\\ATAK-CIV-5.5.1.8-SDK\\\\atak-gradle-takdev.jar



ATAK-Plugin/local.properties



ATAK-Plugin/app/build.gradle



C:\\ATAK-CIV-5.5.1.8-SDK\\atak-gradle-takdev.jar



**Prosjektlokasjon:**

C:\\Users\\bruhe\\StudioProjects\\ATAK-Plugin



## Kommandoer

.\\gradlew build

.\\gradlew --stop

.\\gradlew build --refresh-dependencies

./gradlew assembleCivDebug

.\\gradlew assembleCivDebug --offline (This is the one that is working, wont build otherwise)



keytool -genkeypair -keyalg RSA -keysize 2048 -alias androiddebugkey -keypass android -keystore debug.keystore -storepass android -dname "CN=Android Debug,O=Android,C=US" -validity 9999

#### 

#### Debug prints:

TAKDEV JAR = C:/ATAK-CIV-5.5.1.8-SDK/atak-gradle-takdev.jar

TAKDEV JAR PATH = C:/ATAK-CIV-5.5.1.8-SDK/atak-gradle-takdev.jar


