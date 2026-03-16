#include "MeshtasticHelper.h"
#include <QProcess>
#include <QDebug>

void MeshtasticHelper::sendMessage(const QString &text)
{
    qDebug() << "Sending Meshtastic message:" << text;
    // adjust path if you placed the script elsewhere
    const QString script = QStringLiteral("meshtastic_notify.py");

    QProcess proc;
    proc.start(QStringLiteral("python3"),
               QStringList{script, text});
    if (!proc.waitForFinished(5000)) { // 5‑second timeout
        qWarning("Meshtastic helper timed out");
        proc.kill();
    }
    qDebug() << "Meshtastic process exit code:" << proc.exitCode();
    QByteArray err = proc.readAllStandardError();
    if (!err.isEmpty()) {
        qDebug() << "Meshtastic stderr:" << err;
    }
    QByteArray out = proc.readAllStandardOutput();
    if (!out.isEmpty()) {
        qDebug() << "Meshtastic stdout:" << out;
    }
}