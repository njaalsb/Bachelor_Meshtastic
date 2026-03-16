#include <QApplication>
#include <QThread>
#include <QMutex>
#include <QMessageBox>

#include <QColor>
#include <QtDebug>
#include <QString>
#include <QTimer>
#include <QDateTime>
#include <QBuffer>
#include <QRandomGenerator>
#include <QtEndian>

#include "LeptonThread.h"
#include "MeshtasticHelper.h"
#include "SDRThread.h"

void printUsage(char *cmd) {
        char *cmdname = basename(cmd);
	printf("Usage: %s [OPTION]...\n"
               " -h      display this help and exit\n"
               " -cm x   select colormap\n"
               "           1 : rainbow\n"
               "           2 : grayscale\n"
               "           3 : ironblack [default]\n"
               " -tl x   select type of Lepton\n"
               "           2 : Lepton 2.x [default]\n"
               "           3 : Lepton 3.x\n"
               "               [for your reference] Please use nice command\n"
               "                 e.g. sudo nice -n 0 ./%s -tl 3\n"
               " -ss x   SPI bus speed [MHz] (10 - 30)\n"
               "           20 : 20MHz [default]\n"
               " -min x  override minimum value for scaling (0 - 65535)\n"
               "           [default] automatic scaling range adjustment\n"
               "           e.g. -min 30000\n"
               " -max x  override maximum value for scaling (0 - 65535)\n"
               "           [default] automatic scaling range adjustment\n"
               "           e.g. -max 32000\n"
               " -d x    log level (0-255)\n"
               " -sdr_enable  enable SDR monitoring\n"
               " -sdr_freq x  SDR center frequency in Hz [default 100000000]\n"
               " -sdr_thresh x  SDR signal threshold [default 10000.0]\n"
               "", cmdname, cmdname);
	return;
}

int main( int argc, char **argv )
{
	int typeColormap = 3; // colormap_ironblack
	int typeLepton = 2; // Lepton 2.x
	int spiSpeed = 20; // SPI bus speed 20MHz
	int rangeMin = -1; //
	int rangeMax = -1; //
	int loglevel = 0;
	bool sdrEnable = false;
	uint32_t sdrFreq = 869525000; // 100 MHz
	float sdrThresh = 10000.0f;
	for(int i=1; i < argc; i++) {
		if (strcmp(argv[i], "-h") == 0) {
			printUsage(argv[0]);
			exit(0);
		}
		else if (strcmp(argv[i], "-d") == 0) {
			int val = 3;
			if ((i + 1 != argc) && (strncmp(argv[i + 1], "-", 1) != 0)) {
				val = std::atoi(argv[i + 1]);
				i++;
			}
			if (0 <= val) {
				loglevel = val & 0xFF;
			}
		}
		else if ((strcmp(argv[i], "-cm") == 0) && (i + 1 != argc)) {
			int val = std::atoi(argv[i + 1]);
			if ((val == 1) || (val == 2)) {
				typeColormap = val;
				i++;
			}
		}
		else if ((strcmp(argv[i], "-tl") == 0) && (i + 1 != argc)) {
			int val = std::atoi(argv[i + 1]);
			if (val == 3) {
				typeLepton = val;
				i++;
			}
		}
		else if ((strcmp(argv[i], "-ss") == 0) && (i + 1 != argc)) {
			int val = std::atoi(argv[i + 1]);
			if ((10 <= val) && (val <= 30)) {
				spiSpeed = val;
				i++;
			}
		}
		else if ((strcmp(argv[i], "-min") == 0) && (i + 1 != argc)) {
			int val = std::atoi(argv[i + 1]);
			if ((0 <= val) && (val <= 65535)) {
				rangeMin = val;
				i++;
			}
		}
		else if ((strcmp(argv[i], "-max") == 0) && (i + 1 != argc)) {
			int val = std::atoi(argv[i + 1]);
			if ((0 <= val) && (val <= 65535)) {
				rangeMax = val;
				i++;
			}
		}
		else if (strcmp(argv[i], "-sdr_enable") == 0) {
			sdrEnable = true;
		}
		else if ((strcmp(argv[i], "-sdr_freq") == 0) && (i + 1 != argc)) {
			sdrFreq = (uint32_t)std::atoi(argv[i + 1]);
			i++;
		}
		else if ((strcmp(argv[i], "-sdr_thresh") == 0) && (i + 1 != argc)) {
			sdrThresh = std::atof(argv[i + 1]);
			i++;
		}
	}

	//create the app
	QApplication a( argc, argv );
	
	QImage lastImage;

	//create a thread to gather SPI data
	LeptonThread *thread = new LeptonThread();
	thread->setLogLevel(loglevel);
	thread->useColormap(typeColormap);
	thread->useLepton(typeLepton);
	thread->useSpiSpeedMhz(spiSpeed);
	thread->setAutomaticScalingRange();
	if (0 <= rangeMin) thread->useRangeMinValue(rangeMin);
	if (0 <= rangeMax) thread->useRangeMaxValue(rangeMax);
	QObject::connect(thread, &LeptonThread::updateImage, [&](QImage image) {
		lastImage = image;
	});
	
	//connect ffc button to the thread's ffc action
	// Note: FFC not available in headless mode
	// QObject::connect(button1, SIGNAL(clicked()), thread, SLOT(performFFC()));
	thread->start();
	
	QTimer *saveTimer = new QTimer();
	QObject::connect(saveTimer, &QTimer::timeout, [&]() {
		if (!lastImage.isNull()) {
			qDebug() << "Sending image";
			// Convert to grayscale
			QImage grayImage = lastImage.convertToFormat(QImage::Format_Grayscale8);
			
			// Save to buffer as JPG
			QByteArray buffer;
			QBuffer buf(&buffer);
			buf.open(QIODevice::WriteOnly);
			grayImage.save(&buf, "JPG", 50); // quality 50 for compression
			buf.close();
			
			// Base64 encode
			QByteArray b64 = buffer.toBase64();
			
			// Chunkify
			int maxPayload = 80;
			int total = (b64.size() + maxPayload - 1) / maxPayload;
			quint8 sid = QRandomGenerator::global()->bounded(1, 256);
			
			qDebug() << "Total chunks:" << total << "sid:" << sid;
			for(int idx = 0; idx < total; idx++) {
				QByteArray payload = b64.mid(idx * maxPayload, maxPayload);
				
				// Header: >BHHH big endian: sid (uint8), total (uint16), idx (uint16), len(payload) (uint16) - 7 bytes
				QByteArray header(7, 0);
				header[0] = (char)sid;
				qToBigEndian((quint16)total, (uchar*)header.data() + 1);
				qToBigEndian((quint16)idx, (uchar*)header.data() + 3);
				qToBigEndian((quint16)payload.size(), (uchar*)header.data() + 5);
				
				QByteArray packet = header + payload;
				QByteArray packetB64 = packet.toBase64();
				
				QString msg = QString("IMG|%1|%2|%3").arg(sid).arg(idx).arg(QString(packetB64));
				MeshtasticHelper::sendMessage(msg.toStdString().c_str());
				qDebug() << "Sent chunk" << idx;
				
				// Delay 15s
				QThread::msleep(15000);
			}
			
			// Also save to file
			QString filename = QString("thermal_%1.jpg").arg(QDateTime::currentDateTime().toString("yyyy-MM-dd_hh-mm-ss"));
			grayImage.save(filename);
			qDebug() << "Saved file:" << filename;
		} else {
			qDebug() << "No image to send";
		}
	});
	saveTimer->start(30000); // 30 seconds
	
	if (sdrEnable) {
		SDRThread *sdrThread = new SDRThread();
		sdrThread->setFrequency(sdrFreq);
		sdrThread->setThreshold(sdrThresh);
		// QObject::connect(sdrThread, &SDRThread::signalUpdate, [&](float power) {
		// 	QString msg = QString("Highest SDR signal in last 30s: %1").arg(power);
		// 	MeshtasticHelper::sendMessage(msg.toStdString().c_str());
		// });
		sdrThread->start();
	}
	
	MeshtasticHelper::sendMessage("test");

	return a.exec();
}

