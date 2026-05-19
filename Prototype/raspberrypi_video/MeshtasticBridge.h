#ifndef MESHTASTICBRIDGE_H
#define MESHTASTICBRIDGE_H

#include <QObject>
#include <QProcess>
#include <QString>

class MeshtasticBridge : public QObject
{
    Q_OBJECT
public:
    static MeshtasticBridge& instance();

    void sendMessage(const QString &text);
    void sendRawData(const QByteArray &data, int portNum);

private:
    explicit MeshtasticBridge(QObject *parent = nullptr);
    ~MeshtasticBridge();

    void startBridge();

    QProcess m_process;
};

#endif // MESHTASTICBRIDGE_H