#ifndef MESHTASTICHELPER_H
#define MESHTASTICHELPER_H

#include <QString>

class MeshtasticHelper {
public:
    // send text to the radio; the Python script must be reachable on PATH
    static void sendMessage(const QString &text);
};

#endif // MESHTASTICHELPER_H