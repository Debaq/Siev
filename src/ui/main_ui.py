# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'MainWindowcDApLE.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QMainWindow,
    QMenu, QMenuBar, QPushButton, QSizePolicy,
    QSlider, QSpacerItem, QStatusBar, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

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
        self.actionOD_44 = QAction(MainWindow)
        self.actionOD_44.setObjectName(u"actionOD_44")
        self.actionOD_44.setEnabled(False)
        self.actionOI_44 = QAction(MainWindow)
        self.actionOI_44.setObjectName(u"actionOI_44")
        self.actionOI_44.setEnabled(False)
        self.actionOD_37 = QAction(MainWindow)
        self.actionOD_37.setObjectName(u"actionOD_37")
        self.actionOD_37.setEnabled(False)
        self.actionOI37 = QAction(MainWindow)
        self.actionOI37.setObjectName(u"actionOI37")
        self.actionOI37.setEnabled(False)
        self.actionEspont_neo = QAction(MainWindow)
        self.actionEspont_neo.setObjectName(u"actionEspont_neo")
        self.actionEspont_neo.setEnabled(False)
        self.actionSeguimiento_Lento = QAction(MainWindow)
        self.actionSeguimiento_Lento.setObjectName(u"actionSeguimiento_Lento")
        self.actionSeguimiento_Lento.setEnabled(False)
        self.actionOptoquinetico = QAction(MainWindow)
        self.actionOptoquinetico.setObjectName(u"actionOptoquinetico")
        self.actionOptoquinetico.setEnabled(False)
        self.actionSacadas = QAction(MainWindow)
        self.actionSacadas.setObjectName(u"actionSacadas")
        self.actionSacadas.setEnabled(False)
        self.actionExit = QAction(MainWindow)
        self.actionExit.setObjectName(u"actionExit")
        self.actionNewUser = QAction(MainWindow)
        self.actionNewUser.setObjectName(u"actionNewUser")
        self.actionCalibrar = QAction(MainWindow)
        self.actionCalibrar.setObjectName(u"actionCalibrar")
        self.actionCalibrar.setEnabled(True)
        self.actionAbrir = QAction(MainWindow)
        self.actionAbrir.setObjectName(u"actionAbrir")
        self.actionCambiar_evaluador = QAction(MainWindow)
        self.actionCambiar_evaluador.setObjectName(u"actionCambiar_evaluador")
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

        self.listTestWidget = QTreeWidget(self.centralwidget)
        self.listTestWidget.headerItem().setText(0, "")
        self.listTestWidget.setObjectName(u"listTestWidget")

        self.verticalLayout_3.addWidget(self.listTestWidget)


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
        self.btn_FullScreen.setEnabled(False)

        self.layout_toolbar_video.addWidget(self.btn_FullScreen)

        self.btn_refresh_vng = QPushButton(self.frame_toolbar_video)
        self.btn_refresh_vng.setObjectName(u"btn_refresh_vng")
        self.btn_refresh_vng.setEnabled(False)

        self.layout_toolbar_video.addWidget(self.btn_refresh_vng)

        self.cb_resolution = QComboBox(self.frame_toolbar_video)
        self.cb_resolution.setObjectName(u"cb_resolution")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.cb_resolution.sizePolicy().hasHeightForWidth())
        self.cb_resolution.setSizePolicy(sizePolicy1)

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
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.CameraFrame.sizePolicy().hasHeightForWidth())
        self.CameraFrame.setSizePolicy(sizePolicy2)

        self.horizontalLayout.addWidget(self.CameraFrame)

        self.slider_th_left = QSlider(self.centralwidget)
        self.slider_th_left.setObjectName(u"slider_th_left")
        self.slider_th_left.setOrientation(Qt.Orientation.Vertical)

        self.horizontalLayout.addWidget(self.slider_th_left)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_2)

        self.slider_vertical_cut_up = QSlider(self.centralwidget)
        self.slider_vertical_cut_up.setObjectName(u"slider_vertical_cut_up")
        self.slider_vertical_cut_up.setMinimum(-50)
        self.slider_vertical_cut_up.setMaximum(50)
        self.slider_vertical_cut_up.setTracking(True)
        self.slider_vertical_cut_up.setOrientation(Qt.Orientation.Vertical)
        self.slider_vertical_cut_up.setInvertedAppearance(True)
        self.slider_vertical_cut_up.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.verticalLayout_7.addWidget(self.slider_vertical_cut_up)

        self.slider_vertical_cut_down = QSlider(self.centralwidget)
        self.slider_vertical_cut_down.setObjectName(u"slider_vertical_cut_down")
        self.slider_vertical_cut_down.setMinimum(-50)
        self.slider_vertical_cut_down.setMaximum(50)
        self.slider_vertical_cut_down.setOrientation(Qt.Orientation.Vertical)
        self.slider_vertical_cut_down.setTickPosition(QSlider.TickPosition.TicksBelow)

        self.verticalLayout_7.addWidget(self.slider_vertical_cut_down)

        self.check_simultaneo = QCheckBox(self.centralwidget)
        self.check_simultaneo.setObjectName(u"check_simultaneo")
        self.check_simultaneo.setChecked(True)

        self.verticalLayout_7.addWidget(self.check_simultaneo)

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

        self.lbl_test = QLabel(self.centralwidget)
        self.lbl_test.setObjectName(u"lbl_test")

        self.verticalLayout_2.addWidget(self.lbl_test)


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
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1036, 30))
        self.menuCalofrica = QMenu(self.menubar)
        self.menuCalofrica.setObjectName(u"menuCalofrica")
        self.menuPruebas_Calor_cas = QMenu(self.menuCalofrica)
        self.menuPruebas_Calor_cas.setObjectName(u"menuPruebas_Calor_cas")
        self.menuPruebas_Calor_cas.setEnabled(True)
        self.menuOculomotoras = QMenu(self.menubar)
        self.menuOculomotoras.setObjectName(u"menuOculomotoras")
        self.menuArchivo = QMenu(self.menubar)
        self.menuArchivo.setObjectName(u"menuArchivo")
        self.menuConfiguraci_n = QMenu(self.menubar)
        self.menuConfiguraci_n.setObjectName(u"menuConfiguraci_n")
        self.menuPosicionales = QMenu(self.menubar)
        self.menuPosicionales.setObjectName(u"menuPosicionales")
        self.menuPosicionales.setEnabled(False)
        MainWindow.setMenuBar(self.menubar)

        self.menubar.addAction(self.menuArchivo.menuAction())
        self.menubar.addAction(self.menuCalofrica.menuAction())
        self.menubar.addAction(self.menuOculomotoras.menuAction())
        self.menubar.addAction(self.menuPosicionales.menuAction())
        self.menubar.addAction(self.menuConfiguraci_n.menuAction())
        self.menuCalofrica.addAction(self.actionEspont_neo)
        self.menuCalofrica.addAction(self.menuPruebas_Calor_cas.menuAction())
        self.menuPruebas_Calor_cas.addAction(self.actionOD_44)
        self.menuPruebas_Calor_cas.addAction(self.actionOI_44)
        self.menuPruebas_Calor_cas.addAction(self.actionOD_37)
        self.menuPruebas_Calor_cas.addAction(self.actionOI37)
        self.menuOculomotoras.addAction(self.actionSeguimiento_Lento)
        self.menuOculomotoras.addAction(self.actionOptoquinetico)
        self.menuOculomotoras.addAction(self.actionSacadas)
        self.menuArchivo.addAction(self.actionAbrir)
        self.menuArchivo.addAction(self.actionNewUser)
        self.menuArchivo.addAction(self.actionExit)
        self.menuConfiguraci_n.addAction(self.actionCalibrar)
        self.menuConfiguraci_n.addAction(self.actionCambiar_evaluador)

        self.retranslateUi(MainWindow)

        self.cb_resolution.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionSalir.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
        self.actionCalorica.setText(QCoreApplication.translate("MainWindow", u"Calorica", None))
        self.actionOculomotora.setText(QCoreApplication.translate("MainWindow", u"Oculomotora", None))
        self.actionEspontaneo.setText(QCoreApplication.translate("MainWindow", u"Espontaneo", None))
        self.actionPosicional.setText(QCoreApplication.translate("MainWindow", u"Posicional", None))
        self.actionOD_44.setText(QCoreApplication.translate("MainWindow", u"OD 44", None))
        self.actionOI_44.setText(QCoreApplication.translate("MainWindow", u"OI 44", None))
        self.actionOD_37.setText(QCoreApplication.translate("MainWindow", u"OD 37", None))
        self.actionOI37.setText(QCoreApplication.translate("MainWindow", u"OI 37", None))
        self.actionEspont_neo.setText(QCoreApplication.translate("MainWindow", u"Espont\u00e1neo", None))
        self.actionSeguimiento_Lento.setText(QCoreApplication.translate("MainWindow", u"Seguimiento Lento", None))
        self.actionOptoquinetico.setText(QCoreApplication.translate("MainWindow", u"Optoquinetico", None))
        self.actionSacadas.setText(QCoreApplication.translate("MainWindow", u"Sacadas", None))
        self.actionExit.setText(QCoreApplication.translate("MainWindow", u"Salir", None))
        self.actionNewUser.setText(QCoreApplication.translate("MainWindow", u"Nuevo Usuario...", None))
        self.actionCalibrar.setText(QCoreApplication.translate("MainWindow", u"Calibrar", None))
        self.actionAbrir.setText(QCoreApplication.translate("MainWindow", u"Abrir...", None))
        self.actionCambiar_evaluador.setText(QCoreApplication.translate("MainWindow", u"Cambiar evaluador", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Pruebas", None))
        self.btn_FullScreen.setText(QCoreApplication.translate("MainWindow", u"FullScreen", None))
#if QT_CONFIG(shortcut)
        self.btn_FullScreen.setShortcut(QCoreApplication.translate("MainWindow", u"F", None))
#endif // QT_CONFIG(shortcut)
        self.btn_refresh_vng.setText(QCoreApplication.translate("MainWindow", u"Buscar VNG", None))
        self.cb_resolution.setCurrentText("")
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"...", None))
        self.CameraFrame.setText("")
        self.check_simultaneo.setText("")
        self.btn_start.setText(QCoreApplication.translate("MainWindow", u"Iniciar", None))
#if QT_CONFIG(shortcut)
        self.btn_start.setShortcut(QCoreApplication.translate("MainWindow", u"Space", None))
#endif // QT_CONFIG(shortcut)
        self.btn_fixed.setText(QCoreApplication.translate("MainWindow", u"Fijar", None))
        self.lbl_test.setText("")
        self.lbl_time.setText("")
        self.lbl_text_temp.setText("")
        self.menuCalofrica.setTitle(QCoreApplication.translate("MainWindow", u"VNG", None))
        self.menuPruebas_Calor_cas.setTitle(QCoreApplication.translate("MainWindow", u"Pruebas Calor\u00edcas", None))
        self.menuOculomotoras.setTitle(QCoreApplication.translate("MainWindow", u"Oculomotoras", None))
        self.menuArchivo.setTitle(QCoreApplication.translate("MainWindow", u"Archivo", None))
        self.menuConfiguraci_n.setTitle(QCoreApplication.translate("MainWindow", u"Configuraci\u00f3n", None))
        self.menuPosicionales.setTitle(QCoreApplication.translate("MainWindow", u"Posicionales", None))
    # retranslateUi

