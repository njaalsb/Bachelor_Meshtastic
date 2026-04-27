#include "MeshtasticBridge.h"
#include <QDebug>

MeshtasticBridge& MeshtasticBridge::instance() {
    static MeshtasticBridge inst;
    return inst;
}

MeshtasticBridge::MeshtasticBridge(QObject *parent) : QObject(parent) {
    startBridge();
}

MeshtasticBridge::~MeshtasticBridge() {
    if (m_process.state() == QProcess::Running) {
        m_process.terminate();
        m_process.waitForFinished(2000);
    }
}

void MeshtasticBridge::startBridge() {
    qDebug() << "Starting Meshtastic Bridge process...";
    m_process.start("python3", QStringList() << "meshtasticSendMessage.py");
    
    if (!m_process.waitForStarted()) {
        qCritical() << "Failed to start Meshtastic bridge!";
    }
}

void MeshtasticBridge::sendMessage(const QString &text) {
    if (m_process.state() != QProcess::Running) {
        qWarning() << "Bridge not running, attempting restart...";
        startBridge();
    }

    // Write the message to the Python script's stdin followed by a newline
    m_process.write(text.toUtf8() + "\n");
    m_process.waitForBytesWritten(); 
    qDebug() << "Message queued to bridge:" << text.left(20) << "...";
}

void MeshtasticBridge::sendRawData(const QByteArray &data, int portNum) {
    if (m_process.state() != QProcess::Running) {
        qWarning() << "Bridge not running, attempting restart...";
        startBridge();
    }
    QString line = QString("DATA:%1:%2")
                       .arg(portNum)
                       .arg(QString::fromLatin1(data.toHex()));
    m_process.write(line.toUtf8() + "\n");
    m_process.waitForBytesWritten();
    qDebug() << "Raw data queued port=" << portNum << "bytes=" << data.size();
}