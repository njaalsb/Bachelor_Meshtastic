#ifndef MESHTASTICHELPER_H
#define MESHTASTICHELPER_H

#include <QObject>
#include <QProcess>
#include <QString>

class MeshtasticHelper : public QObject
{
    Q_OBJECT
public:
    // Access the single instance of the helper
    static MeshtasticHelper& instance();

    // The function you call from Main.cpp
    void sendMessage(const QString &text);

private:
    explicit MeshtasticHelper(QObject *parent = nullptr);
    ~MeshtasticHelper();

    QProcess m_process;
    void startBridge();
};

#endif // MESHTASTICHELPER_H