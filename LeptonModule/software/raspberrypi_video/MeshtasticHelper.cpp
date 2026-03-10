#include "MeshtasticHelper.h"
#include <QProcess>

void MeshtasticHelper::sendMessage(const QString &text)
{
    // adjust path if you placed the script elsewhere
    const QString script = QStringLiteral("meshtastic_notify.py");

    QProcess proc;
    proc.start(QStringLiteral("python3"),
               QStringList{script, text});
    if (!proc.waitForFinished(3000)) { // 3‑second timeout
        qWarning("Meshtastic helper timed out");
    }
}