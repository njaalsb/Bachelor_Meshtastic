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
    qDebug() << "starting meshtastic bridge";
    m_process.start("python3", QStringList() << "meshtasticSendMessage.py");
    if (!m_process.waitForStarted())
        qCritical() << "failed to start bridge";
}

void MeshtasticBridge::sendMessage(const QString &text) {
    if (m_process.state() != QProcess::Running) {
        qWarning() << "bridge failed, restarting";
        startBridge();
    }
    m_process.write(text.toUtf8() + "\n");
    m_process.waitForBytesWritten();
}

void MeshtasticBridge::sendRawData(const QByteArray &data, int portNum) {
    if (m_process.state() != QProcess::Running) {
        qWarning() << "bridge failed, restarting";
        startBridge();
    }
    QString line = QString("DATA:%1:%2").arg(portNum).arg(QString::fromLatin1(data.toHex()));
    m_process.write(line.toUtf8() + "\n");
    m_process.waitForBytesWritten();
    qDebug() << "port=" << portNum << "bytes=" << data.size();
}