#include "MeshtasticHelper.h"
#include <QDebug>

MeshtasticHelper& MeshtasticHelper::instance() {
    static MeshtasticHelper inst;
    return inst;
}

MeshtasticHelper::MeshtasticHelper(QObject *parent) : QObject(parent) {
    startBridge();
}

MeshtasticHelper::~MeshtasticHelper() {
    if (m_process.state() == QProcess::Running) {
        m_process.terminate();
        m_process.waitForFinished(2000);
    }
}

void MeshtasticHelper::startBridge() {
    qDebug() << "Starting Meshtastic Bridge process...";
    // Ensure the path to your python script is correct
    m_process.start("python3", QStringList() << "meshtastic_notify.py");
    
    if (!m_process.waitForStarted()) {
        qCritical() << "Failed to start Meshtastic bridge!";
    }
}

void MeshtasticHelper::sendMessage(const QString &text) {
    if (m_process.state() != QProcess::Running) {
        qWarning() << "Bridge not running, attempting restart...";
        startBridge();
    }

    // Write the message to the Python script's stdin followed by a newline
    m_process.write(text.toUtf8() + "\n");
    m_process.waitForBytesWritten(); 
    qDebug() << "Message queued to bridge:" << text.left(20) << "...";
}