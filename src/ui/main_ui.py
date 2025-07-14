# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindowEWLDEV.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QSlider, QSpacerItem, QStatusBar, QToolButton,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1036, 807)
        self.actionSalir = QAction(MainWindow)
        self.actionSalir.setObjectName(u"actionSalir")
        self.actionCalorica = QAction(MainWindow)
        self.actionCalorica.setObjectName(u"actionCalorica")
        self.actionOculomotora = QAction(MainWindow)
        self.actionOculomotora.setObjectName(u"actionOculomotora")
        self.actionEspontaneo = QAction(MainWindow)
        self.actionEspontaneo.setObjectName(u"actionEspontaneo")
        self.actionPosicional = QAction(MainWindow)
        self.actionPosicional.setObjectName(u"actionPosicional")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_4 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, -1, -1, -1)
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, -1, -1, -1)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label.sizePolicy().hasHeightForWidth())
        self.label.setSizePolicy(sizePolicy)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_3.addWidget(self.label)

        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName(u"listWidget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.listWidget.sizePolicy().hasHeightForWidth())
        self.listWidget.setSizePolicy(sizePolicy1)

        self.verticalLayout_3.addWidget(self.listWidget)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(-1, -1, -1, 0)
        self.frame_toolbar_video = QFrame(self.centralwidget)
        self.frame_toolbar_video.setObjectName(u"frame_toolbar_video")
        self.frame_toolbar_video.setMaximumSize(QSize(16777215, 30))
        self.layout_toolbar_video = QHBoxLayout(self.frame_toolbar_video)
        self.layout_toolbar_video.setObjectName(u"layout_toolbar_video")
        self.layout_toolbar_video.setContentsMargins(-1, 0, -1, 0)
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.layout_toolbar_video.addItem(self.horizontalSpacer_2)

        self.btn_FullScreen = QPushButton(self.frame_toolbar_video)
        self.btn_FullScreen.setObjectName(u"btn_FullScreen")

        self.layout_toolbar_video.addWidget(self.btn_FullScreen)

        self.cb_resolution = QComboBox(self.frame_toolbar_video)
        self.cb_resolution.addItem(u"1028x720@120")
        self.cb_resolution.addItem(u"960x540@120")
        self.cb_resolution.addItem(u"640x360@210")
        self.cb_resolution.addItem(u"420x240@210")
        self.cb_resolution.addItem(u"320x240@210")
        self.cb_resolution.setObjectName(u"cb_resolution")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.cb_resolution.sizePolicy().hasHeightForWidth())
        self.cb_resolution.setSizePolicy(sizePolicy2)

        self.layout_toolbar_video.addWidget(self.cb_resolution)

        self.toolButton = QToolButton(self.frame_toolbar_video)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.toolButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

        self.layout_toolbar_video.addWidget(self.toolButton)


        self.verticalLayout_2.addWidget(self.frame_toolbar_video)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, 0, -1, -1)
        self.slider_erode_right = QSlider(self.centralwidget)
        self.slider_erode_right.setObjectName(u"slider_erode_right")
        self.slider_erode_right.setMaximum(10)
        self.slider_erode_right.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_3.addWidget(self.slider_erode_right)

        self.slider_nose_width = QSlider(self.centralwidget)
        self.slider_nose_width.setObjectName(u"slider_nose_width")
        self.slider_nose_width.setMaximum(50)
        self.slider_nose_width.setSingleStep(0)
        self.slider_nose_width.setPageStep(10)
        self.slider_nose_width.setValue(25)
        self.slider_nose_width.setOrientation(Qt.Orientation.Horizontal)
        self.slider_nose_width.setInvertedAppearance(False)
        self.slider_nose_width.setInvertedControls(False)
        self.slider_nose_width.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_nose_width.setTickInterval(5)

        self.horizontalLayout_3.addWidget(self.slider_nose_width)

        self.slider_erode_left = QSlider(self.centralwidget)
        self.slider_erode_left.setObjectName(u"slider_erode_left")
        self.slider_erode_left.setMaximum(10)
        self.slider_erode_left.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_3.addWidget(self.slider_erode_left)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(-1, 0, -1, -1)
        self.slider_th_right = QSlider(self.centralwidget)
        self.slider_th_right.setObjectName(u"slider_th_right")
        self.slider_th_right.setOrientation(Qt.Orientation.Vertical)

        self.horizontalLayout.addWidget(self.slider_th_right)

        self.CameraFrame = QLabel(self.centralwidget)
        self.CameraFrame.setObjectName(u"CameraFrame")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.CameraFrame.sizePolicy().hasHeightForWidth())
        self.CameraFrame.setSizePolicy(sizePolicy3)

        self.horizontalLayout.addWidget(self.CameraFrame)

        self.slider_th_left = QSlider(self.centralwidget)
        self.slider_th_left.setObjectName(u"slider_th_left")
        self.slider_th_left.setOrientation(Qt.Orientation.Vertical)

        self.horizontalLayout.addWidget(self.slider_th_left)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_2)

        self.verticalSlider = QSlider(self.centralwidget)
        self.verticalSlider.setObjectName(u"verticalSlider")
        self.verticalSlider.setOrientation(Qt.Orientation.Vertical)

        self.verticalLayout_7.addWidget(self.verticalSlider)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer)


        self.horizontalLayout.addLayout(self.verticalLayout_7)


        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)

        self.btn_start = QPushButton(self.centralwidget)
        self.btn_start.setObjectName(u"btn_start")

        self.horizontalLayout_5.addWidget(self.btn_start)

        self.btn_fixed = QPushButton(self.centralwidget)
        self.btn_fixed.setObjectName(u"btn_fixed")
        self.btn_fixed.setLocale(QLocale(QLocale.English, QLocale.UnitedStates))
        self.btn_fixed.setCheckable(True)

        self.horizontalLayout_5.addWidget(self.btn_fixed)


        self.verticalLayout_2.addLayout(self.horizontalLayout_5)


        self.horizontalLayout_2.addLayout(self.verticalLayout_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.lbl_time = QLabel(self.centralwidget)
        self.lbl_time.setObjectName(u"lbl_time")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout.addWidget(self.lbl_time)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.verticalLayout.addItem(self.horizontalSpacer)

        self.lbl_text_temp = QLabel(self.centralwidget)
        self.lbl_text_temp.setObjectName(u"lbl_text_temp")

        self.verticalLayout.addWidget(self.lbl_text_temp)


        self.horizontalLayout_2.addLayout(self.verticalLayout)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, -1, -1)
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")

        self.horizontalLayout_4.addLayout(self.verticalLayout_5)

        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(-1, 0, -1, 0)
        self.layout_graph = QHBoxLayout()
        self.layout_graph.setObjectName(u"layout_graph")
        self.layout_graph.setContentsMargins(-1, 30, -1, -1)

        self.verticalLayout_8.addLayout(self.layout_graph)

        self.slider_time = QSlider(self.centralwidget)
        self.slider_time.setObjectName(u"slider_time")
        self.slider_time.setOrientation(Qt.Orientation.Horizontal)

        self.verticalLayout_8.addWidget(self.slider_time)


        self.horizontalLayout_4.addLayout(self.verticalLayout_8)

        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")

        self.horizontalLayout_4.addLayout(self.verticalLayout_6)


        self.verticalLayout_4.addLayout(self.horizontalLayout_4)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1036, 30))
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuNuevo = QMenu(self.menuArchivo)
        self.menuNuevo.setObjectName(u"menuNuevo")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menuArchivo.addAction(self.menuNuevo.menuAction())
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction(self.actionSalir)
        self.menuNuevo.addAction(self.actionCalorica)
        self.menuNuevo.addAction(self.actionOculomotora)
        self.menuNuevo.addAction(self.actionEspontaneo)
        self.menuNuevo.addAction(self.actionPosicional)

        self.retranslateUi(MainWindow)

        self.cb_resolution.setCurrentIndex(1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
        self.actionCalorica.setText(QCoreApplication.translate("MainWindow", u"Calorica", None))
        self.actionOculomotora.setText(QCoreApplication.translate("MainWindow", u"Oculomotora", None))
        self.actionEspontaneo.setText(QCoreApplication.translate("MainWindow", u"Espontaneo", None))
        self.actionPosicional.setText(QCoreApplication.translate("MainWindow", u"Posicional", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Pruebas Previas", None))
        self.btn_FullScreen.setText(QCoreApplication.translate("MainWindow", u"FullScreen", None))
#if QT_CONFIG(shortcut)
        self.btn_FullScreen.setShortcut(QCoreApplication.translate("MainWindow", u"F", None))
#endif // QT_CONFIG(shortcut)

        self.cb_resolution.setCurrentText(QCoreApplication.translate("MainWindow", u"960x540@120", None))
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.CameraFrame.setText("")
        self.btn_start.setText(QCoreApplication.translate("MainWindow", u"Start", None))
#if QT_CONFIG(shortcut)
        self.btn_start.setShortcut(QCoreApplication.translate("MainWindow", u"Space", None))
#endif // QT_CONFIG(shortcut)
        self.btn_fixed.setText(QCoreApplication.translate("MainWindow", u"Fixed", None))
        self.lbl_time.setText("")
        self.lbl_text_temp.setText("")
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"Archivo", None))
        self.menuNuevo.setTitle(QCoreApplication.translate("MainWindow", u"Nuevo..", None))
    # retranslateUi

