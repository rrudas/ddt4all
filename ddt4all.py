#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import glob
import json
import PyQt4.QtGui as gui
import PyQt4.QtCore as core
import parameters, ecu
import elm, options, locale
import dataeditor
import sniffer
import imp
import traceback

__author__ = "Cedric PAILLE"
__copyright__ = "Copyright 2016-2017"
__credits__ = []
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Cedric PAILLE"
__email__ = "cedricpaille@gmail.com"
__status__ = "Beta"

_ = options.translator('ddt4all_main')
app = None

class Ecu_list(gui.QWidget):
    def __init__(self, ecuscan, treeview_ecu):
        super(Ecu_list, self).__init__()
        self.selected = ''
        self.treeview_ecu = treeview_ecu
        self.vehicle_combo = gui.QComboBox()

        self.ecu_map = {
            "01": "ABS-VDC [$01]",
            "2C": "Airbag-SRS [$2C]",
            "0D": "Automatic Parking Brake [$0D]",
            "6E": "Automatic Transmission [$6E]",
            "13": "Audio [$13]",
            "00": "CAN Primary network [$00]",
            "7A": "ECM Engine Control Module [$7A]",
            "04": "EPS Electric Power Steering [$04]",
            "07": "HLS Hi Beam Lighting System [$07]",
            "29": "HVAC Climate Control [$29]",
            "70": "Head Light [$70]",
            "72": "Head Light Right [$72]",
            "71": "Head Light Left [$71]",
            "79": "LNG [$79]",
            "3F": "Navigation [$3F]",
            "58": "Navigation [$58]",
            "0E": "Parking Sonar [$0E]",
            "51": "Cluster Meter [$51]",
            "1C": "RCU Roof Control Unit [$1C]",
            "26": "UCH - BCM [$26]",
            "27": "UPC - USM [$27]"
        }

        vehicles = [
            "ALL", "X06 - TWINGO", "X44 - TWINGO II", "X07 - TWINGO III", "X77 - MODUS",
            "X35 - SYMBOL/THALIA", "X65 - CLIO II", "X85 - CLIO III", "X98 - CLIO IV",
            "X87 - CAPTUR", "X38 - FLUENCE", "XFF - FLUENCE II", "X64 - MEGANE/SCENIC I",
            "X84 - MEGANE/SCENIC II", "X95 - MEGANE/SCENIC III", "XFB - MEGANE IV",
            "XFA - SCENIC IV", "X56 - LAGUNA", "X74 - LAGUNA II", "X91 - LAGUNA III",
            "X47 - LAGUNA III (tricorps)", "X66 - ESPACE III", 
            "X81 - ESPACE IV", "XFC - ESPACE V",
            "X73 - VELSATIS", "X43 - LATITUDE", "XFD - TALISMAN", "H45 - KOLEOS",
            "XZG - KOLEOS II", "XFE - KADJAR", "X33 - WIND", "X09 - TWIZY",
            "X10 - ZOE",
            "X76 - KANGOO I", "X61 - KANGOO II", "X24 - MASCOTT", "X83 - TRAFFIC II",
            "X82 - TRAFFIC III", "X70 - MASTER II", "X62 - MASTER III", "X90 - LOGAN/SANDERO",
            "X52 - LOGAN/SANDERO II", "X79 - DUSTER", "XJD - DUSTER II", "X67 - DOKKER",
            "X92 - LODGY", "X02 - MICRA (NISSAN)", "X21 - NOTE (NISSAN)"
        ]

        for v in vehicles:
            self.vehicle_combo.addItem(v)

        self.vehicle_combo.activated.connect(self.filterProject)

        layout = gui.QVBoxLayout()
        layout.addWidget(self.vehicle_combo)
        self.setLayout(layout)
        self.list = gui.QTreeWidget(self)
        self.list.setSelectionMode(gui.QAbstractItemView.SingleSelection)
        layout.addWidget(self.list)
        self.ecuscan = ecuscan
        self.list.doubleClicked.connect(self.ecuSel)
        self.init()

    def init(self):
        self.list.clear()
        self.list.setColumnCount(3)
        self.list.model().setHeaderData(0, core.Qt.Horizontal, _('ECU name'))
        self.list.model().setHeaderData(1, core.Qt.Horizontal, _('Projets'))
        self.list.model().setHeaderData(2, core.Qt.Horizontal, _('Protocol'))

        stored_ecus = {"Custom": []}

        custom_files = glob.glob("./json/*.json.targets")

        for cs in custom_files:
            f = open(cs, "r")
            jsoncontent = f.read()
            f.close()

            target = json.loads(jsoncontent)

            if not target:
                grp = "Custom"
                projects_list = []
                protocol = ''
            else:
                target = target[0]
                protocol = target['protocol']
                projects_list = target['projects']
                if target['address'] not in self.ecu_map:
                    grp = "Custom"
                else:
                    grp = self.ecu_map[target['address']]

            if not grp in stored_ecus:
                stored_ecus[grp] = []

            projects = "/".join(projects_list)
            name = u' (' + projects + u')'

            stored_ecus[grp].append([cs[:-8][7:], name, protocol])

        for ecu in self.ecuscan.ecu_database.targets:
            if ecu.addr not in self.ecu_map:
                grp = ecu.group
                grp += " [$" + str(ecu.addr).zfill(2) + "]"
            else:
                grp = self.ecu_map[ecu.addr]

            if not grp in stored_ecus:
                stored_ecus[grp] = []

            projects = "/".join(ecu.projects)
            name = u' (' + projects + u')'

            if not [ecu.name, name, ecu.protocol] in stored_ecus[grp]:
                stored_ecus[grp].append([ecu.name, name, ecu.protocol])

        keys = stored_ecus.keys()
        keys.sort(cmp=locale.strcoll)
        for e in keys:
            item = gui.QTreeWidgetItem(self.list, [e])
            for t in stored_ecus[e]:
                gui.QTreeWidgetItem(item, t)

    def filterProject(self):
        project = str(self.vehicle_combo.currentText()[0:3])
        root = self.list.invisibleRootItem()
        root_items = [root.child(i) for i in range(root.childCount())]

        for root_item in root_items:
            root_hidden = True

            items = [root_item.child(i) for i in range(root_item.childCount())]
            for item in items:
                if (project.upper() in str(item.text(1).toAscii()).upper()) or project == "ALL":
                    item.setHidden(False)
                    root_hidden = False
                else:
                    item.setHidden(True)
            root_item.setHidden(root_hidden)

    def ecuSel(self, index):
        if index.parent() == core.QModelIndex():
            return
        item = self.list.model().itemData(self.list.model().index(index.row(), 0, index.parent()))
        selected = unicode(item[0].toPyObject().toUtf8(), encoding="UTF-8")
        target = self.ecuscan.ecu_database.getTarget(selected)
        if target:
            self.ecuscan.addTarget(target)
        if selected:
            self.treeview_ecu.addItem(selected)


class Main_widget(gui.QMainWindow):
    def __init__(self, parent = None):
        super(Main_widget, self).__init__(parent)
        self.plugins = {}
        self.setWindowTitle(_("DDT4All"))
        print _("Scanning ECUs...")
        self.ecu_scan = ecu.Ecu_scanner()
        self.ecu_scan.qapp = app
        options.ecu_scanner = self.ecu_scan
        print ("%i " + _("loaded ECUs in database.")) % self.ecu_scan.getNumEcuDb()

        self.paramview = None
        self.screennames = []

        self.statusBar = gui.QStatusBar()
        self.setStatusBar(self.statusBar)

        self.connectedstatus = gui.QLabel()
        self.connectedstatus.setAlignment(core.Qt.AlignHCenter | core.Qt.AlignVCenter)
        self.protocolstatus = gui.QLabel()
        self.progressstatus = gui.QProgressBar()
        self.infostatus = gui.QLabel()

        self.connectedstatus.setFixedWidth(100)
        self.protocolstatus.setFixedWidth(200)
        self.progressstatus.setFixedWidth(150)
        self.infostatus.setFixedWidth(200)

        self.refreshtimebox = gui.QSpinBox()
        self.refreshtimebox.setRange(100, 2000)
        self.refreshtimebox.setSingleStep(100)
        self.refreshtimebox.valueChanged.connect(self.changeRefreshTime)
        refrestimelabel = gui.QLabel(_("Refresh rate (ms):"))

        self.statusBar.addWidget(self.connectedstatus)
        self.statusBar.addWidget(self.protocolstatus)
        self.statusBar.addWidget(self.progressstatus)
        self.statusBar.addWidget(refrestimelabel)
        self.statusBar.addWidget(self.refreshtimebox)
        self.statusBar.addWidget(self.infostatus)

        self.tabbedview = gui.QTabWidget()
        self.setCentralWidget(self.tabbedview)

        self.scrollview = gui.QScrollArea()
        self.scrollview.setWidgetResizable(False)

        self.snifferview = sniffer.sniffer()

        self.tabbedview.addTab(self.scrollview, _("Screen"))
        self.tabbedview.addTab(self.snifferview, _("CAN Sniffer"))

        if options.simulation_mode:
            self.buttonEditor = dataeditor.buttonEditor()
            self.requesteditor = dataeditor.requestEditor()
            self.dataitemeditor = dataeditor.dataEditor()
            self.ecuparameditor = dataeditor.ecuParamEditor()
            self.tabbedview.addTab(self.requesteditor, _("Requests"))
            self.tabbedview.addTab(self.dataitemeditor, _("Data"))
            self.tabbedview.addTab(self.buttonEditor, _("Buttons"))
            self.tabbedview.addTab(self.ecuparameditor, _("Ecu parameters"))

        screen_widget = gui.QWidget()
        self.treedock_widget = gui.QDockWidget(self)
        self.treedock_widget.setWidget(screen_widget)
        self.treeview_params = gui.QTreeWidget()
        self.screenmenu = gui.QMenuBar()
        treedock_layout = gui.QVBoxLayout()
        treedock_layout.addWidget(self.screenmenu)
        treedock_layout.addWidget(self.treeview_params)
        screen_widget.setLayout(treedock_layout)
        self.treeview_params.setHeaderLabels([_("Screens")])
        self.treeview_params.clicked.connect(self.changeScreen)

        actionmenu = self.screenmenu.addMenu(_("Action"))
        cat_action = gui.QAction(_("New Category"), actionmenu)
        screen_action = gui.QAction(_("New Screen"), actionmenu)
        rename_action = gui.QAction(_("Rename"), actionmenu)
        actionmenu.addAction(cat_action)
        actionmenu.addAction(screen_action)
        actionmenu.addAction(rename_action)
        cat_action.triggered.connect(self.newCategory)
        screen_action.triggered.connect(self.newScreen)
        rename_action.triggered.connect(self.screenRename)

        self.treedock_logs = gui.QDockWidget(self)
        self.logview = gui.QTextEdit()
        self.logview.setReadOnly(True)
        self.treedock_logs.setWidget(self.logview)

        self.treedock_ecu = gui.QDockWidget(self)
        self.treeview_ecu = gui.QListWidget(self.treedock_ecu)
        self.treedock_ecu.setWidget(self.treeview_ecu)
        self.treeview_ecu.clicked.connect(self.changeECU)

        self.eculistwidget = Ecu_list(self.ecu_scan, self.treeview_ecu)
        self.treeview_eculist = gui.QDockWidget(self)
        self.treeview_eculist.setWidget(self.eculistwidget)

        self.addDockWidget(core.Qt.LeftDockWidgetArea, self.treeview_eculist)
        self.addDockWidget(core.Qt.LeftDockWidgetArea, self.treedock_ecu)
        self.addDockWidget(core.Qt.LeftDockWidgetArea, self.treedock_widget)
        self.addDockWidget(core.Qt.BottomDockWidgetArea, self.treedock_logs)

        self.toolbar = self.addToolBar(_("File"))

        scanaction = gui.QAction(gui.QIcon("icons/scan.png"), _("Scan ECUs"), self)
        scanaction.triggered.connect(self.scan)

        self.diagaction = gui.QAction(gui.QIcon("icons/dtc.png"), _("Read DTC"), self)
        self.diagaction.triggered.connect(self.readDtc)
        self.diagaction.setEnabled(False)

        self.log = gui.QAction(gui.QIcon("icons/log.png"), _("Full log"), self)
        self.log.setCheckable(True)
        self.log.setChecked(options.log_all)
        self.log.triggered.connect(self.changeLogMode)

        self.expert = gui.QAction(gui.QIcon("icons/expert.png"), _("Expert mode (enable writing)"), self)
        self.expert.setCheckable(True)
        self.expert.setChecked(options.promode)
        self.expert.triggered.connect(self.changeUserMode)

        self.autorefresh = gui.QAction(gui.QIcon("icons/autorefresh.png"), _("Auto refresh"), self)
        self.autorefresh.setCheckable(True)
        self.autorefresh.setChecked(options.auto_refresh)
        self.autorefresh.triggered.connect(self.changeAutorefresh)

        self.refresh = gui.QAction(gui.QIcon("icons/refresh.png"), _("Refresh (one shot)"), self)
        self.refresh.triggered.connect(self.refreshParams)
        self.refresh.setEnabled(not options.auto_refresh)

        self.hexinput = gui.QAction(gui.QIcon("icons/hex.png"), _("Manual command"), self)
        self.hexinput.triggered.connect(self.hexeditor)
        self.hexinput.setEnabled(False)

        self.toolbar.addAction(scanaction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.log)
        self.toolbar.addAction(self.expert)
        self.toolbar.addAction(self.autorefresh)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.refresh)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.diagaction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.hexinput)

        vehicle_dir = "vehicles"
        if not os.path.exists(vehicle_dir):
            os.mkdir(vehicle_dir)

        ecu_files = []
        for filename in os.listdir(vehicle_dir):
            basename, ext = os.path.splitext(filename)
            if ext == '.ecu':
                ecu_files.append(basename)

        menu = self.menuBar()

        diagmenu = menu.addMenu(_("File"))
        newecuction = diagmenu.addAction(_("Create New ECU"))
        saveecuaction = diagmenu.addAction(_("Save current ECU"))
        diagmenu.addSeparator()
        savevehicleaction = diagmenu.addAction(_("Save ECU list"))
        savevehicleaction.triggered.connect(self.saveEcus)
        saveecuaction.triggered.connect(self.saveEcu)
        newecuction.triggered.connect(self.newEcu)
        diagmenu.addSeparator()
        zipdbaction = diagmenu.addAction(_("Zip database"))
        zipdbaction.triggered.connect(self.zipdb)
        diagmenu.addSeparator()

        for ecuf in ecu_files:
            ecuaction = diagmenu.addAction(ecuf)
            ecuaction.triggered.connect(lambda state, a=ecuf: self.loadEcu(a))

        plugins_menu = menu.addMenu(_("Plugins"))
        category_menus = {}
        plugins = glob.glob("./plugins/*.py")
        for plugin in plugins:
            try:
                modulename = os.path.basename(plugin).replace(".py", "")
                plug = imp.load_source(modulename, plugin)

                category = plug.category
                name = plug.plugin_name
                need_hw = plug.need_hw

                #if options.simulation_mode and need_hw:
                #    continue

                if not category in category_menus:
                    category_menus[category] = plugins_menu.addMenu(category)

                plug_action = category_menus[category].addAction(name)
                plug_action.triggered.connect(lambda state, a=plug.plugin_entry: self.launchPlugin(a))

                self.plugins[modulename] = plug
            except Exception as e:
                print _("Cannot load plugin %s, %s") % (plugin, traceback.format_exc())

        self.setConnected(True)

    def zipdb(self):
        self.logview.append("Zipping XML database... (this can take a few minutes)")
        core.QCoreApplication.processEvents()
        parameters.zipConvertXML()

    def launchPlugin(self, pim):
        if self.paramview:
            self.paramview.init('')
        pim()
        if self.paramview:
            self.paramview.initELM()

    def screenRename(self):
        item = self.treeview_params.currentItem()
        if not item:
            return

        itemname = unicode(item.text(0).toUtf8(), encoding="UTF-8")
        nin = gui.QInputDialog.getText(self, 'DDT4All', _('Enter new name'))

        if not nin[1]:
            return

        newitemname = unicode(nin[0].toUtf8(), encoding="UTF-8")

        if newitemname == itemname:
            return

        if item.parent():
            self.screennames.remove(itemname)
            self.screennames.append(newitemname)
            self.paramview.renameScreen(itemname, newitemname)
        else:
            self.paramview.renameCategory(itemname, newitemname)

        item.setText(0, newitemname)

    def newCategory(self):
        ncn = gui.QInputDialog.getText(self, 'DDT4All', _('Enter category name'))
        necatname = unicode(ncn[0].toUtf8(), encoding="UTF-8")
        if necatname:
            self.paramview.createCategory(necatname)
            self.treeview_params.addTopLevelItem(gui.QTreeWidgetItem([necatname]))

    def newScreen(self):
        item = self.treeview_params.currentItem()

        if not item:
            self.logview.append("<font color=red>" + _("Please select a category before creating new screen") + "</font>")
            return

        if item.parent() is not None:
            item = item.parent()

        category = unicode(item.text(0).toUtf8(), encoding="UTF-8")
        nsn = gui.QInputDialog.getText(self, 'DDT4All', _('Enter screen name'))

        if not nsn[1]:
            return

        newscreenname = unicode(nsn[0].toUtf8(), encoding="UTF-8")
        if newscreenname:
            self.paramview.createScreen(newscreenname, category)

            item.addChild(gui.QTreeWidgetItem([newscreenname]))
            self.screennames.append(newscreenname)

    def showDataTab(self, name):
        self.tabbedview.setCurrentIndex(3)
        self.dataitemeditor.edititem(name)

    def hexeditor(self):
        if self.paramview:
            # Stop auto refresh
            options.auto_refresh = False
            self.refresh.setEnabled(False)
            self.paramview.hexeditor()

    def changeRefreshTime(self):
        if self.paramview:
            self.paramview.setRefreshTime(self.refreshtimebox.value())

    def scan(self):
        msgBox = gui.QMessageBox()
        msgBox.setText(_('Scan options'))
        scancan = False
        scankwp = False

        msgBox.addButton(gui.QPushButton('CAN'), gui.QMessageBox.YesRole)
        msgBox.addButton(gui.QPushButton('KWP'), gui.QMessageBox.NoRole)
        msgBox.addButton(gui.QPushButton('KWP&&CAN'), gui.QMessageBox.RejectRole)
        role = msgBox.exec_()

        if role == 0:
            self.logview.append(_("Scanning CAN"))
            scancan = True

        if role == 1:
            self.logview.append(_("Scanning KWP"))
            scankwp = True

        if role == 2:
            self.logview.append(_("Scanning CAN&KWP"))
            scankwp = True
            scancan = True

        progressWidget = gui.QWidget(None)
        progressLayout = gui.QVBoxLayout()
        progressWidget.setLayout(progressLayout)
        self.progressstatus.setRange(0, self.ecu_scan.getNumAddr())
        self.progressstatus.setValue(0)

        self.ecu_scan.clear()
        if scancan:
            self.ecu_scan.scan(self.progressstatus, self.infostatus)
        if scankwp:
            self.ecu_scan.scan_kwp(self.progressstatus, self.infostatus)

        self.treeview_ecu.clear()
        self.treeview_params.clear()
        if self.paramview:
            self.paramview.init(None)

        for ecu in self.ecu_scan.ecus.keys():
            item = gui.QListWidgetItem(ecu)
            self.treeview_ecu.addItem(item)

        for ecu in self.ecu_scan.approximate_ecus.keys():
            item = gui.QListWidgetItem(ecu)
            item.setForeground(core.Qt.red)
            self.treeview_ecu.addItem(item)

        self.progressstatus.setValue(0)

    def setConnected(self, on):
        if options.simulation_mode:
            self.connectedstatus.setStyleSheet("background : orange")
            self.connectedstatus.setText(_("EDITION MODE"))
            return
        if on:
            self.connectedstatus.setStyleSheet("background : green")
            self.connectedstatus.setText(_("CONNECTED"))
        else:
            self.connectedstatus.setStyleSheet("background : red")
            self.connectedstatus.setText(_("DISCONNECTED"))

    def saveEcus(self):
        filename = gui.QFileDialog.getSaveFileName(self, _("Save vehicule (keep '.ecu' extension)"),
                                                    "./vehicles/mycar.ecu", "*.ecu")
        if filename == "":
            return

        eculist = []
        numecus = self.treeview_ecu.count()
        for i in range(numecus):
            item = self.treeview_ecu.item(i)
            eculist.append(unicode(item.text().toUtf8(), encoding="UTF-8"))

        jsonfile = open(filename, "w")
        jsonfile.write(json.dumps(eculist))
        jsonfile.close()

    def newEcu(self):
        filename = gui.QFileDialog.getSaveFileName(self, _("Save ECU (keep '.json' extension)"), "./json/myecu.json",
                                                   "*.json")

        basename = os.path.basename(unicode(filename.toUtf8(), encoding="UTF-8"))
        filename = os.path.join("./json", basename)
        ecufile = ecu.Ecu_file(None)
        layout = open(filename + ".layout", "w")
        layout.write('{"screens": {}, "categories":{"Category":[]} }')
        layout.close()

        targets = open(filename + ".targets", "w")
        targets.write('[]')
        targets.close()

        layout = open(filename, "w")
        layout.write(ecufile.dumpJson())
        layout.close()

        item = gui.QListWidgetItem(basename)
        self.treeview_ecu.addItem(item)

    def saveEcu(self):
        if self.paramview:
            self.paramview.saveEcu()
        self.eculistwidget.init()
        self.eculistwidget.filterProject()

    def loadEcu(self, name):
        vehicle_file = "vehicles/" + name + ".ecu"
        # self.ecu_scan.ecus = pickle.load(open(vehicle_file, "rb"))
        #

        jsonfile = open(vehicle_file, "r")
        eculist = json.loads(jsonfile.read())
        jsonfile.close()

        self.treeview_ecu.clear()
        self.treeview_params.clear()
        if self.paramview:
            self.paramview.init(None)

        for ecu in eculist:
            item = gui.QListWidgetItem(ecu)
            self.treeview_ecu.addItem(item)

    def readDtc(self):
        if self.paramview:
            self.paramview.readDTC()

    def changeAutorefresh(self):
        options.auto_refresh = self.autorefresh.isChecked()
        self.refresh.setEnabled(not options.auto_refresh)

        if options.auto_refresh:
            if self.paramview:
                self.paramview.updateDisplays(True)

    def refreshParams(self):
        if self.paramview:
            self.paramview.updateDisplays(True)

    def changeUserMode(self):
        options.promode = self.expert.isChecked()

    def changeLogMode(self):
        options.log_all = self.log.isChecked()

    def readDTC(self):
        if self.paramview:
            self.paramview.readDTC()

    def changeScreen(self, index):
        item = self.treeview_params.model().itemData(index)
        screen = unicode(item[0].toPyObject().toUtf8(), encoding="UTF-8")
        inited = self.paramview.init(screen)
        self.diagaction.setEnabled(inited)
        self.hexinput.setEnabled(inited)
        self.expert.setChecked(False)
        options.promode = False
        self.autorefresh.setChecked(False)
        options.auto_refresh = False
        self.refresh.setEnabled(True)

        if options.simulation_mode and self.paramview.layoutdict:
            if screen in self.paramview.layoutdict['screens']:
                self.buttonEditor.set_layout(self.paramview.layoutdict['screens'][screen])

        self.paramview.setRefreshTime(self.refreshtimebox.value())

    def closeEvent(self, event):
        self.snifferview.stopthread()
        super(Main_widget, self).closeEvent(event)

    def changeECU(self, index):
        item = self.treeview_ecu.model().itemData(index)
        ecu_name = unicode(item[0].toString().toUtf8(), encoding="UTF-8")

        isxml = True
        ecu_file = None

        if ".json" in ecu_name:
            ecu_file = ecu_name
            ecu_addr = ""
            isxml = False
        elif ecu_name in self.ecu_scan.ecus:
            ecu = self.ecu_scan.ecus[ecu_name]
        elif ecu_name in self.ecu_scan.approximate_ecus:
            ecu = self.ecu_scan.approximate_ecus[ecu_name]
        else:
            ecu = self.ecu_scan.ecu_database.getTarget(ecu_name)

        if not ecu_file:
            ecu_file = options.ecus_dir + ecu.href
            ecu_addr = ecu.addr

        if self.snifferview.set_file(ecu_file):
            self.tabbedview.setCurrentIndex(1)

        if self.paramview:
            if ecu_file == self.paramview.ddtfile:
                return

        self.diagaction.setEnabled(True)
        self.hexinput.setEnabled(True)
        self.treeview_params.clear()

        uiscale_mem = 12

        if self.paramview:
            uiscale_mem = self.paramview.uiscale
            self.paramview.setParent(None)
            self.paramview.close()
            self.paramview.destroy()

        self.paramview = parameters.paramWidget(self.scrollview, ecu_file, ecu_addr, ecu_name, self.logview, self.protocolstatus)
        if options.simulation_mode:
            self.requesteditor.set_ecu(self.paramview.ecurequestsparser)
            self.dataitemeditor.set_ecu(self.paramview.ecurequestsparser)
            self.buttonEditor.set_ecu(self.paramview.ecurequestsparser)
            self.ecuparameditor.set_ecu(self.paramview.ecurequestsparser)
            self.ecuparameditor.set_targets(self.paramview.targetsdata)
            if isxml:
                self.requesteditor.enable_view(False)
                self.dataitemeditor.enable_view(False)
                self.buttonEditor.enable_view(False)
                self.ecuparameditor.enable_view(False)

        self.paramview.uiscale = uiscale_mem

        self.scrollview.setWidget(self.paramview)
        screens = self.paramview.categories.keys()
        self.screennames = []
        for screen in screens:
            item = gui.QTreeWidgetItem(self.treeview_params, [screen])
            for param in self.paramview.categories[screen]:
                param_item = gui.QTreeWidgetItem(item, [param])
                param_item.setData(0, core.Qt.UserRole, param)
                self.screennames.append(param)

class donationWidget(gui.QLabel):
    def __init__(self):
        super(donationWidget, self).__init__()
        img = gui.QPixmap("icons/donate.png")
        self.setPixmap(img)
        self.setAlignment(core.Qt.AlignCenter)

    def mousePressEvent(self, mousevent):
        msgbox = gui.QMessageBox()
        msgbox.setText(_("<center>This Software is free, but I need money to buy cables/ECUs and make this application more reliable</center>"))
        okbutton = gui.QPushButton(_('Yes I contribute'))
        msgbox.addButton(okbutton, gui.QMessageBox.YesRole)
        msgbox.addButton(gui.QPushButton(_("No, I don't")), gui.QMessageBox.NoRole)
        okbutton.clicked.connect(self.donate)
        msgbox.exec_()

    def donate(self):
        url = core.QUrl("https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=cedricpaille@gmail.com&lc=CY&item_name=codetronic&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donateCC_LG.if:NonHosted", core.QUrl.TolerantMode)
        gui.QDesktopServices().openUrl(url)
        msgbox = gui.QMessageBox()
        msgbox.setText(_("<center>Thank you for you contribution, if nothing happens, please go to : https://github.com/cedricp/ddt4all</center>"))
        msgbox.exec_()


class portChooser(gui.QDialog):
    def __init__(self):
        portSpeeds = [38400, 57600, 115200, 230400, 500000]
        self.port = None
        self.mode = 0
        self.securitycheck = False
        self.selectedportspeed = 38400
        super(portChooser, self).__init__(None)
        layout = gui.QVBoxLayout()
        label = gui.QLabel(self)
        label.setText(_("ELM port selection"))
        label.setAlignment(core.Qt.AlignHCenter | core.Qt.AlignVCenter)
        donationwidget = donationWidget()
        self.setLayout(layout)
        
        self.listview = gui.QListWidget(self)

        layout.addWidget(donationwidget)
        layout.addWidget(label)
        layout.addWidget(self.listview)

        medialayout = gui.QHBoxLayout()
        self.usbbutton = gui.QPushButton()
        self.usbbutton.setIcon(gui.QIcon("icons/usb.png"))
        self.usbbutton.setIconSize(core.QSize(60, 60))
        self.usbbutton.setFixedHeight(64)
        self.usbbutton.setFixedWidth(64)
        self.usbbutton.setCheckable(True)
        medialayout.addWidget(self.usbbutton)

        self.wifibutton = gui.QPushButton()
        self.wifibutton.setIcon(gui.QIcon("icons/wifi.png"))
        self.wifibutton.setIconSize(core.QSize(60, 60))
        self.wifibutton.setFixedHeight(64)
        self.wifibutton.setFixedWidth(64)
        self.wifibutton.setCheckable(True)
        medialayout.addWidget(self.wifibutton)

        self.btbutton = gui.QPushButton()
        self.btbutton.setIcon(gui.QIcon("icons/bt.png"))
        self.btbutton.setIconSize(core.QSize(60, 60))
        self.btbutton.setFixedHeight(64)
        self.btbutton.setFixedWidth(64)
        self.btbutton.setCheckable(True)
        medialayout.addWidget(self.btbutton)

        self.obdlinkbutton = gui.QPushButton()
        self.obdlinkbutton.setIcon(gui.QIcon("icons/obdlink.png"))
        self.obdlinkbutton.setIconSize(core.QSize(60, 60))
        self.obdlinkbutton.setFixedHeight(64)
        self.obdlinkbutton.setFixedWidth(64)
        self.obdlinkbutton.setCheckable(True)
        medialayout.addWidget(self.obdlinkbutton)

        layout.addLayout(medialayout)

        self.btbutton.toggled.connect(self.bt)
        self.wifibutton.toggled.connect(self.wifi)
        self.usbbutton.toggled.connect(self.usb)
        self.obdlinkbutton.toggled.connect(self.obdlink)

        speedlayout = gui.QHBoxLayout()
        self.speedcombo = gui.QComboBox()
        speedlabel = gui.QLabel(_("Port speed"))
        speedlayout.addWidget(speedlabel)
        speedlayout.addWidget(self.speedcombo)

        for s in portSpeeds:
            self.speedcombo.addItem(str(s))

        self.speedcombo.setCurrentIndex(0)

        layout.addLayout(speedlayout)

        button_layout = gui.QHBoxLayout()
        button_con = gui.QPushButton(_("Connected mode"))
        button_dmo = gui.QPushButton(_("Edition mode"))
        button_elm_chk = gui.QPushButton(_("ELM benchmark"))

        wifilayout = gui.QHBoxLayout()
        wifilabel = gui.QLabel(_("WiFi port : "))
        self.wifiinput = gui.QLineEdit()
        self.wifiinput.setText("192.168.0.10:35000")
        wifilayout.addWidget(wifilabel)
        wifilayout.addWidget(self.wifiinput)
        layout.addLayout(wifilayout)

        safetychecklayout = gui.QHBoxLayout()
        self.safetycheck = gui.QCheckBox()
        self.safetycheck.setChecked(False)
        safetylabel = gui.QLabel(_("I'm aware that I can harm my car if badly used"))
        safetychecklayout.addWidget(self.safetycheck)
        safetychecklayout.addWidget(safetylabel)
        layout.addLayout(safetychecklayout)

        button_layout.addWidget(button_con)
        button_layout.addWidget(button_dmo)
        button_layout.addWidget(button_elm_chk)
        layout.addLayout(button_layout)

        self.logview = gui.QTextEdit()
        layout.addWidget(self.logview)
        self.logview.hide()

        button_con.clicked.connect(self.connectedMode)
        button_dmo.clicked.connect(self.demoMode)
        button_elm_chk.clicked.connect(self.check_elm)

        self.timer = core.QTimer()
        self.timer.timeout.connect(self.rescan_ports)
        self.timer.start(200)
        self.portcount = -1

    def check_elm(self):
        currentitem = self.listview.currentItem()
        if currentitem:
            self.logview.show()
            port = str(currentitem.text().split('[')[0])
            speed = int(self.speedcombo.currentText())
            res = elm.elm_checker(port, speed, self.logview, core.QCoreApplication)
            if res == False:
                self.logview.append(options.get_last_error())

    def rescan_ports(self):
        ports = elm.get_available_ports()
        if ports == None:
            self.listview.clear()
            self.portcount = 0
            return

        if len(ports) == self.portcount:
            return


        self.listview.clear()
        self.portcount = len(ports)
        for p in ports:
            item = gui.QListWidgetItem(self.listview)
            item.setText(p[0] + "[" + p[1] + "]")

        self.timer.start(1000)

    def bt(self):
        self.wifibutton.blockSignals(True)
        self.btbutton.blockSignals(True)
        self.usbbutton.blockSignals(True)
        self.obdlinkbutton.blockSignals(True)

        self.speedcombo.setCurrentIndex(2)
        self.btbutton.setChecked(True)
        self.wifibutton.setChecked(False)
        self.usbbutton.setChecked(False)
        self.wifiinput.setEnabled(False)
        self.speedcombo.setEnabled(True)
        self.obdlinkbutton.setChecked(False)

        self.wifibutton.blockSignals(False)
        self.btbutton.blockSignals(False)
        self.usbbutton.blockSignals(False)
        self.obdlinkbutton.blockSignals(False)

    def wifi(self):
        self.wifibutton.blockSignals(True)
        self.btbutton.blockSignals(True)
        self.usbbutton.blockSignals(True)
        self.obdlinkbutton.blockSignals(True)

        self.wifibutton.setChecked(True)
        self.btbutton.setChecked(False)
        self.usbbutton.setChecked(False)
        self.wifiinput.setEnabled(True)
        self.speedcombo.setEnabled(False)
        self.obdlinkbutton.setChecked(False)

        self.wifibutton.blockSignals(False)
        self.btbutton.blockSignals(False)
        self.usbbutton.blockSignals(False)
        self.obdlinkbutton.blockSignals(False)

    def usb(self):
        self.wifibutton.blockSignals(True)
        self.btbutton.blockSignals(True)
        self.usbbutton.blockSignals(True)
        self.obdlinkbutton.blockSignals(True)

        self.usbbutton.setChecked(True)
        self.speedcombo.setCurrentIndex(0)
        self.btbutton.setChecked(False)
        self.wifibutton.setChecked(False)
        self.wifiinput.setEnabled(False)
        self.speedcombo.setEnabled(True)
        self.obdlinkbutton.setChecked(False)

        self.wifibutton.blockSignals(False)
        self.btbutton.blockSignals(False)
        self.usbbutton.blockSignals(False)
        self.obdlinkbutton.blockSignals(False)

    def obdlink(self):
        self.wifibutton.blockSignals(True)
        self.btbutton.blockSignals(True)
        self.usbbutton.blockSignals(True)
        self.obdlinkbutton.blockSignals(True)

        self.usbbutton.setChecked(False)
        self.speedcombo.setCurrentIndex(2)
        self.btbutton.setChecked(False)
        self.wifibutton.setChecked(False)
        self.wifiinput.setEnabled(False)
        self.speedcombo.setEnabled(True)
        self.obdlinkbutton.setChecked(True)

        self.wifibutton.blockSignals(False)
        self.btbutton.blockSignals(False)
        self.usbbutton.blockSignals(False)
        self.obdlinkbutton.blockSignals(False)

    def connectedMode(self):
        self.timer.stop()
        self.securitycheck = self.safetycheck.isChecked()
        self.selectedportspeed = int(self.speedcombo.currentText())
        if not pc.securitycheck:
            msgbox = gui.QMessageBox()
            msgbox.setText(_("You must check the recommandations"))
            msgbox.exec_()
            return

        if self.wifibutton.isChecked():
            self.port = str(self.wifiinput.text())
            self.mode = 1
            self.done(True)
        else:
            currentitem = self.listview.currentItem()
            if currentitem:
                self.port = str(currentitem.text().split('[')[0])
                self.mode = 1
                self.done(True)
            else:
                msgbox = gui.QMessageBox()
                msgbox.setText(_("Please select a communication port"))
                msgbox.exec_()

    def demoMode(self):
        self.timer.stop()
        self.securitycheck = self.safetycheck.isChecked()
        self.port = 'DUMMY'
        self.mode = 2
        options.report_data = False
        self.done(True)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    options.simultation_mode = True
    app = gui.QApplication(sys.argv)

    if sys.platform[:3] != "win":
        font = gui.QFont("Sans", 9)
        font.setBold(False)
        app.setFont(font)
        app.setStyle("windows")

    ecudirfound = False

    if os.path.exists(options.ecus_dir + '/eculist.xml'):
        print _("Using custom DDT database")
        ecudirfound = True

    if not ecudirfound and os.path.exists("C:/DDT2000data/ecus"):
        print _("Using DDT2000 default installation")
        options.ecus_dir = "C:/DDT2000data/ecus/"
        ecudirfound = True

    pc = portChooser()
    nok = True
    while nok:
        pcres = pc.exec_()

        if pc.mode == 0 or pcres == gui.QDialog.Rejected:
            exit(0)
        if pc.mode == 1:
            options.promode = False
            options.simulation_mode = False
        if pc.mode == 2:
            options.promode = False
            options.simulation_mode = True
            break

        options.port = str(pc.port)
        port_speed = pc.selectedportspeed

        if not options.port:
            msgbox = gui.QMessageBox()
            msgbox.setText(_("No COM port selected"))
            msgbox.exec_()

        print _("Initilizing ELM with speed %i...") % port_speed
        options.elm = elm.ELM(options.port, port_speed)

        if options.elm_failed:
            pc.show()
            pc.logview.append(options.get_last_error())
            msgbox = gui.QMessageBox()
            msgbox.setText(_("No ELM327 or OBDLINK-SX detected on COM port ") + options.port)
            msgbox.exec_()
        else:
            nok = False

    w = Main_widget()
    options.main_window = w
    w.show()
    app.exec_()
