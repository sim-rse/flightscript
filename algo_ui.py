import GUI
import addPointDialog as ptdlg
import addZoneDialog as zndlg
from pointlib import *
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QPolygonF
from UI_ressources import MapView
from pointlib import *

from algo import get_links_and_dist, main, cls
import settings

class CustomWindow(GUI.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        self.waypoints = []
        self.BASE = None
        self.noflyzones = []
        self.settings = {
            "margin": 1,
            "scale": 1 
        }
        self.loadedProject = "waypoints.json"
        self.loadFile(self.loadedProject)
        

    def loadFile(self, path):
        if path:
            self.loadedProject = path
            self.settings = loadsettings(path)
            settings.SCALE = self.settings["scale"]
            settings.MARGIN = self.settings["margin"]

            self.waypoints, self.noflyzones, self.BASE = loadWaypoints(path, settings.MARGIN)
            

    def globalUpdate(self, fileJustLoaded = False):
        self.updatePoints()
        self.updateZones()
        self.baseLabel.setText(self.BASE.name)
        self.make_graph(fileJustLoaded)
        
        self.zoneMargin.setText(str(settings.MARGIN))

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.graphicsView = MapView(parent=self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(290, 10, 421, 481))
        self.graphicsView.setObjectName("graphicsView")

        self.startButton.clicked.connect(self.startSim)
        self.zoneMargin.textEdited.connect(self.margin_text_changed)
        self.actionLoad_project.triggered.connect(self.loadProject)
        self.actionReload_project.triggered.connect(self.reloadProject)
        self.addPointButton.clicked.connect(self.addPointbutton_clicked)
        self.addZoneButton.clicked.connect(self.addZoneButton_clicked)

        self.waypointsFrame.setStyleSheet("#waypointwidget {\n"
"border: 1px solid rgb(182, 184, 195);\n"
"background-color: qlineargradient(spread:pad, x1:0.0400505, y1:1, x2:0.672, y2:0.0738636, stop:0 rgba(205, 205, 205, 255), stop:1 rgba(238, 238, 238, 255))\n"
"}")
        self.noflyzonesFrame.setStyleSheet("#noflyzonewidget {\n"
"border: 1px solid rgb(182, 184, 195);\n"
"background-color: qlineargradient(spread:pad, x1:0.0400505, y1:1, x2:0.672, y2:0.0738636, stop:0 rgba(205, 205, 205, 255), stop:1 rgba(238, 238, 238, 255))\n"
"}")
        self.menubar.setStyleSheet("""
QMenuBar {
    font-size: 12px;          /* smaller text */
}

QMenuBar::item {
    padding: 2px 10px;        /* reduce vertical + horizontal padding */
    margin: 0px;
}

QMenuBar::item:selected {
    background: #ccc;
}""")
        
        self.globalUpdate()

    def margin_text_changed(self,text):
        try:
            text = int(text)
            for zone in self.noflyzones:
                if not zone.fixedmargin:
                    zone.margin = text
            self.make_graph()
        except:
            print(f"Margin text input is not the right type, ignoring till correct")
        

    def loadProject(self,_):
        fname = QFileDialog.getOpenFileName(None, "Open File", ".", "Json files (*.json);; All files (*)")
        if fname[0]:
            self.loadFile(fname[0])
            self.globalUpdate(True)

    def reloadProject(self):
        self.loadFile(self.loadedProject)
        self.globalUpdate(True)

    def saveProject(self):
        fname = QFileDialog.getSaveFileName(None, "Save File", ".", "Json files (*.json);; All files (*)")


    def startSim(self):

        settings.EMPTY_MASS = float(self.emptyMass.text())  # kg
        settings.BATTERY_ENERGY = float(self.batteryCap.text()) * 3600  #multiply Wh by 3600 to get the energy in Joules
        settings.MAX_PAYLOAD = float(self.maxPayload.text())

        settings.CRUISE_ALTITUDE = float(self.cruiseAlt.text())
        settings.SAFETY_RESERVE = float(self.safetyMargin.text())

        settings.CD = float(self.cd.text())
        settings.RHO = float(self.rho.text())
        settings.KANTELHOEK = float(self.kantelhoek.text())
        settings.A = float(self.area.text())

        settings.MAXLIFT = float(self.maxLift.text())   

        match self.comboBox.currentIndex():
            case 0:
                settings.ROUTETYPE = "single"
            case 1:
                settings.ROUTETYPE = "two"
            case 2:
                settings.ROUTETYPE = "all"

        #calculations
        cls()
        main_route, r1,r2 = main(self.waypoints,self.noflyzones, self.BASE)
        
        self.make_graph()
        if self.comboBox.currentIndex() == 0:
            self.draw_route(main_route)
        else:
            self.draw_routes((r1, r2))

    def addPointbutton_clicked(self):
        dialog = AddPointDialog()
        if dialog.exec():
            data = dialog.get_data()
            if data["use_xy"]:
                print('using xy')
                coord_type = "xy"
            else:
                coord_type = "gps"

            if data["payload"] > settings.MAX_PAYLOAD:
                msg = QMessageBox(QMessageBox.Icon.Warning, "Warning","The payload entered is too high for the current drone configuration!" )
                msg.exec()
                return
            try:
                point_idx = len(self.waypoints)+1
                print(f"adding waypoint with settings: {data["lat"]} , {data["lon"]} , {data["payload"]} , {coord_type} , {data["name"]}")
                point = WayPoint(data["lat"],data["lon"],data["payload"],coord_type, data["name"], origin_lat=settings.ORIGIN[0], origin_lon=settings.ORIGIN[1], idx = point_idx)
                self.addPoint(point)
            except:
                msg = QMessageBox(QMessageBox.Icon.Critical, "Error","Couldn't add point, please check if what you entered is correct and complete!" )
                #msg.setIcon(QMessageBox.Icon.Critical)
                msg.exec()

    def editPointbutton_clicked(self, waypoint:WayPoint):
        dialog = AddPointDialog(edit = True)

        data = {
            "name": waypoint.name,
            "coord_type": waypoint.preferred_coord,
            "x": waypoint.x,
            "y": waypoint.y,
            "lat": waypoint.lat,
            "lon": waypoint.lon, 
            "payload": waypoint.payload
        }
        dialog.load_data(data)
        if dialog.exec():
            data = dialog.get_data()
            if data["use_xy"]:
                coord_type = "xy"
            else:
                coord_type = "gps"
            waypoint.preferred_coord = coord_type
            if data["payload"] > settings.MAX_PAYLOAD:
                msg = QMessageBox(QMessageBox.Icon.Warning, "Warning","The payload entered is too high for ther current drone configuration!" )
                msg.exec()
                return
            waypoint.name = data["name"]
            waypoint.payload = data["payload"]
            waypoint.setcoords(data["lat"], data["lon"], coord_type)

            self.globalUpdate()

    def addPoint(self, waypoint):
        self.waypoints.append(waypoint)
        self.updatePointIndexes()
        self.updatePoints()
        self.make_graph()
    

    def deletePoint(self, waypoint):
        if waypoint == self.BASE:
            msg = QMessageBox(QMessageBox.Icon.Warning, "Warning","You are trying to remove the Base which will lead to errors if you dont select a new one.\n\nProceed anyway?", QMessageBox.StandardButton.Abort|QMessageBox.StandardButton.Yes)
            
            if msg.exec() == QMessageBox.StandardButton.Yes: 
                self.waypoints.remove(waypoint)
                self.BASE = None
        else:
            self.waypoints.remove(waypoint)
        
        self.updatePointIndexes()
        self.globalUpdate()

    def changeBase(self, point:WayPoint):
        self.BASE = point

    def addZoneButton_clicked(self):
        dialog = AddZoneDialog()
        if dialog.exec():
            data = dialog.get_data()
            if "margin" in data:
                margin = data["margin"]
                fixedmargin = True
            else:
                margin = settings.MARGIN
                fixedmargin = False
            zone = NoFlyZone(data["bounds"], name=data["name"], idx=len(self.noflyzones)+1,margin=margin,fixedmargin=fixedmargin)
            self.noflyzones.append(zone)
            self.globalUpdate()
        
    def editZoneButton_clicked(self, zone:NoFlyZone):
        dialog = AddZoneDialog(edit = True)

        data = {
            "name": zone.name,
            "bounds": zone.bounds
        }

        if zone.fixedmargin:
            data["margin"]=zone.margin

        dialog.load_data(data)
        if dialog.exec():
            data = dialog.get_data()
            if "margin" in data:
                margin = data["margin"]
                fixedmargin = True
            else:
                margin = settings.MARGIN
                fixedmargin = False
            zone.bounds = data["bounds"]
            zone.name = data["name"]
            zone.margin = margin
            zone.fixedmargin = fixedmargin

            self.globalUpdate()
            
    def addZone(self, zone):
        self.noflyzones.append(zone)

    def deleteZone(self, zone):
        self.noflyzones.remove(zone)
        self.updateZones()
        self.make_graph()
    
    def updatePointIndexes(self):
        idx = 0
        for point in self.waypoints:
            point.idx = idx
            idx +=1

    def updatePoints(self):
        for child in self.waypointsFrame.children():
            child.deleteLater()

        y = 0
        widget_height = 31
        for point in self.waypoints:
            widget = QtWidgets.QWidget(parent=self.waypointsFrame)
            widget.setGeometry(QtCore.QRect(0, y, 225, widget_height))
            widget.setMinimumHeight(widget_height)
            widget.setObjectName("waypointwidget")

            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText(point.name)

            gearButton = QtWidgets.QPushButton(parent=widget)
            gearButton.setGeometry(QtCore.QRect(170, 0, 31, widget_height))
            gearButton.setText("")
            gearButton.clicked.connect(lambda _, p=point: self.editPointbutton_clicked(p))
            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 31, widget_height))
            deleteButton.setText("X")
            deleteButton.clicked.connect(lambda _, p=point: self.deletePoint(p))       #clicked.connect automatically gives only one bool as arg to the function, but you can give extra arguments if you use the lambda function (the lambda will get the bool and you can pass whatever you'd like)
            icon = QtGui.QIcon()                                                       # i also used this weird p=point to get the current value of point. if you just pass point to deletePoint the latest point value (so the last one of the for loop) will apply to all buttons!
            icon.addPixmap(QtGui.QPixmap("ressources/gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
            gearButton.setIcon(icon)

            y+=31
            widget.show()       #else they don't swot up after a second update
        self.waypointsFrame.setGeometry(QtCore.QRect(0, 0, 241, y))
        self.scrollAreaWidgetContents.setMinimumSize(QtCore.QSize(0, y))

    def updateZones(self):
        for child in self.noflyzonesFrame.children():
            child.deleteLater()

        y = 0
        widget_height = 31
        for zone in self.noflyzones:
            
            widget = QtWidgets.QWidget(parent=self.noflyzonesFrame)
            widget.setGeometry(QtCore.QRect(0, y, 225, widget_height))
            widget.setMinimumHeight(widget_height)
            widget.setObjectName("noflyzonewidget")

            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText(zone.name)

            gearButton = QtWidgets.QPushButton(parent=widget)
            gearButton.setGeometry(QtCore.QRect(170, 0, 31, widget_height))
            gearButton.setText("")
            gearButton.clicked.connect(lambda _, z=zone: self.editZoneButton_clicked(z))
            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 31, widget_height))
            deleteButton.setText("X")
            deleteButton.clicked.connect(lambda _, z=zone: self.deleteZone(z))

            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("ressources/gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
            gearButton.setIcon(icon)

            y+=31
            widget.show()       #else they don't show up after a second update
        self.noflyzonesFrame.setGeometry(QtCore.QRect(0, 0, 241, y))
        self.scrollAreaWidgetContents_2.setMinimumSize(QtCore.QSize(0, y))


    def make_graph(self, fileJustLoaded = False):
        self.graphicsView.clear()
        # -----------------------------
        # map background
        # -----------------------------

        # optional map image
        # self.graphicsView.draw_background("map.png")
        if "background_outline" in self.settings:
            self.graphicsView.draw_outline(self.settings["background_outline"], color=QColor(150,150,150), scale = self.settings["scale"])
        # -----------------------------
        # no-fly zones
        # -----------------------------
        
        # draw zones
        for zone in self.noflyzones:
            self.graphicsView.draw_zone(zone.margin_zone, scale=settings.SCALE, text=False)
            self.graphicsView.draw_zone(zone, color= QColor(0,255,0), scale=settings.SCALE)

        links_matrix, _ = get_links_and_dist(self.waypoints,self.noflyzones)
        n = len(links_matrix)

        if settings.DRAW_LINKS:
            # draw links
            for i in range(n):
            #only iterating for the upper triangle of the matrix (and doing the lower at the same time)
                for j in range(i+1,n):      #i+1 for skipping the diagonal
                    self.graphicsView.draw_path(links_matrix[i][j].path, scale=settings.SCALE)

        for point in self.waypoints:
            self.graphicsView.draw_point(point, QColor("blue"), 8,text=True,scale=settings.SCALE)

        if self.BASE:
            self.graphicsView.draw_point(self.BASE, QColor("orange"), 8,scale=settings.SCALE)

        

        if fileJustLoaded:
            #resets transform (scroll) & cursor
            self.graphicsView.resetview()       #see UI_ressources.py !

    def draw_route(self, route, color = QColor(0, 0, 200)):
        for link in route:
            self.graphicsView.draw_path(link.path, color=color,scale=settings.SCALE)
    
    def draw_routes(self, routes):
        colors = [QColor(0,150,150), QColor(100,100,100), QColor(200,200,0), QColor(200,0,200),QColor(100,200,100)]
        color_index = 0
        for route in routes:
            self.draw_route(route,color=colors[color_index%(len(colors)-1)])
            color_index += 1
       
class AddPointDialog(QDialog):
    def __init__(self, parent = None, edit = False, boundpoint=False):
        super().__init__(parent=parent)
        self.ui = ptdlg.Ui_Dialog()
        self.ui.setupUi(self)

        if edit: 
            _translate = QtCore.QCoreApplication.translate
            self.setWindowTitle(_translate("Dialog", "Edit Point"))
            self.ui.addLabel.setText(_translate("Dialog", "Edit WayPoint"))
        if boundpoint:
            _translate = QtCore.QCoreApplication.translate
            self.setWindowTitle(_translate("Dialog", "Add bound point"))
            self.ui.addLabel.setText(_translate("Dialog", "Add bound point"))
            self.ui.nameEdit.setPlaceholderText("No name needed")
            self.ui.nameEdit.setEnabled(False)
            self.ui.payloadEdit.setPlaceholderText("No payload needed")
            self.ui.payloadEdit.setEnabled(False)
        self.ui.okButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)

        self.ui.usexyCheckBox.toggled.connect(self.checkBoxChanged)

    def checkBoxChanged(self):
        _translate = QtCore.QCoreApplication.translate
        if self.ui.usexyCheckBox.isChecked():
            self.ui.latLabel.setText(_translate("Dialog", "Point X:"))
            self.ui.latEdit.setPlaceholderText(_translate("Dialog", "Insert X coordinate..."))
            self.ui.longLabel.setText(_translate("Dialog", "Point Y"))
            self.ui.longEdit.setPlaceholderText(_translate("Dialog", "Insert Y coordinate..."))
        else:
            self.ui.latLabel.setText(_translate("Dialog", "Point latitude: "))
            self.ui.latEdit.setPlaceholderText(_translate("Dialog", "insert latitude..."))
            self.ui.longLabel.setText(_translate("Dialog", "Point longitude: "))
            self.ui.longEdit.setPlaceholderText(_translate("Dialog", "insert longitude..."))

    def get_data(self):
        if self.ui.latEdit.text() == "":
            if self.ui.usexyCheckBox.isChecked(): 
                lat = 0
            else:
                lat = settings.ORIGIN[0]
        else: 
            lat = float(self.ui.latEdit.text())
        if self.ui.longEdit.text() == "":
            if self.ui.usexyCheckBox.isChecked():
                long = 0
            else: 
                long = settings.ORIGIN[1]
        else: 
            long = float(self.ui.longEdit.text())
        if self.ui.payloadEdit.text() == "":
            payload = 0
        else: 
            payload = float(self.ui.payloadEdit.text())
        if self.ui.nameEdit.text() == "":
            name = "Waypoint" 
        else: 
            name = self.ui.nameEdit.text()
        print('returning: ', lat, long)
        return {
            "name": name,
            "lat": lat,
            "lon": long,
            "payload": payload,
            "use_xy": self.ui.usexyCheckBox.isChecked()
        }

    def load_data(self, data):
        self.ui.nameEdit.setText(data["name"])
        self.ui.payloadEdit.setText(str(data["payload"]))
        if data["coord_type"] == "xy":
            self.ui.usexyCheckBox.setChecked(True)
            self.ui.latEdit.setText(str(data["x"]))
            self.ui.longEdit.setText(str(data["y"]))
        else:
            self.ui.usexyCheckBox.setChecked(False)
            self.ui.latEdit.setText(str(data["lat"]))
            self.ui.longEdit.setText(str(data["lon"]))

class AddZoneDialog(QDialog):
    def __init__(self, parent = None, edit=False):
        super().__init__(parent=parent)
        self.ui = zndlg.Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.okButton.clicked.connect(self.accept)
        self.ui.cancelButton.clicked.connect(self.reject)
        self.ui.addzoneButton.clicked.connect(self.addPoint)
        self.ui.checkBox.checkStateChanged.connect(self.checkboxCheckChange)
        self.bounds = []
        self.updatePoints()

        
        if edit: 
            _translate = QtCore.QCoreApplication.translate
            self.setWindowTitle(_translate("Dialog", "Edit Zone"))

    def addPoint(self):
        dialog = AddPointDialog(boundpoint = True)
        if dialog.exec():
            data = dialog.get_data()
            if data["use_xy"]:
                print('using xy')
                coord_type = "xy"
            else:
                coord_type = "gps"

            point = Point(data["lat"],data["lon"],coord_type, origin_lat=settings.ORIGIN[0], origin_lon=settings.ORIGIN[1])
            self.bounds.append(point)
            self.updatePoints()
    
    def get_data(self):
        if self.ui.nameEdit.text() == "":
            name = "noFlyZone" 
        else: 
            name = self.ui.nameEdit.text()
        data = {"name":name, "bounds":self.bounds}

        if self.ui.checkBox.isChecked():
            try:
                data["margin"] = int(self.ui.marginEdit.text())
            except:
                print("Error while converting margin to int")
                print(self.ui.marginEdit.text())
                print(type(self.ui.marginEdit.text()))
                data["margin"] = 0
        return data
    
    def load_data(self, data:list):
        self.ui.nameEdit.setText(data["name"])
        self.bounds = data["bounds"]
        if "margin" in data:
            self.ui.marginEdit.setText(str(data["margin"]))
            self.ui.checkBox.setChecked(True)
        self.updatePoints()
    
    
    def updatePoints(self):
        for child in self.ui.frame.children():
            if child != self.ui.addzoneButton:
                child.hide()
                child.deleteLater()

        y = 0
        widget_height = 30
        for point in self.bounds:
            widget = QtWidgets.QWidget(parent=self.ui.frame)
            widget.setGeometry(QtCore.QRect(0, y, 225, widget_height))
            widget.setMinimumHeight(widget_height)
            widget.setObjectName("waypointwidget")

            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText("Point")

            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 30, widget_height))
            deleteButton.setText("X")
            deleteButton.clicked.connect(lambda _, p=point: self.deletePoint(p))       #clicked.connect automatically gives only one bool as arg to the function, but you can give extra arguments if you use the lambda function (the lambda will get the bool and you can pass whatever you'd like)
            icon = QtGui.QIcon()                                                       # i also used this weird p=point to get the current value of point. if you just pass point to deletePoint the latest point value (so the last one of the for loop) will apply to all buttons!
            icon.addPixmap(QtGui.QPixmap("ressources/gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)

            y+=30
            widget.show()       #else they don't show up after a second update
        self.ui.frame.show()
        self.ui.addzoneButton.move(QtCore.QPoint(0,y))
        
        y+= self.ui.addzoneButton.height()
        self.ui.frame.setGeometry(QtCore.QRect(0, 0, 231, y))
        self.ui.scrollAreaWidgetContents.setMinimumSize(QtCore.QSize(0, y))
    
    def updatePoints_(self):
        # Clear layout
        while self.ui.pointsLayout.count():
            item = self.ui.pointsLayout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # Rebuild list
        for point in self.bounds:
            widget = QtWidgets.QWidget()
            widget.setSizePolicy(
                QtWidgets.QSizePolicy.Policy.Expanding,
                QtWidgets.QSizePolicy.Policy.Fixed
            )
            widget.setMinimumHeight(30)
            widget.setMaximumHeight(30)

            layout = QtWidgets.QHBoxLayout(widget)
            layout.setContentsMargins(5, 0, 5, 0)

            label = QtWidgets.QLabel("Point")

            deleteButton = QtWidgets.QPushButton("X")
            deleteButton.setFixedSize(20, 20)
            deleteButton.clicked.connect(lambda _, p=point: self.deletePoint(p))

            layout.addWidget(label)
            layout.addStretch()
            layout.addWidget(deleteButton)

            self.ui.pointsLayout.addWidget(widget)

        # Keep items at top WITHOUT breaking scrolling
        self.ui.pointsLayout.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

    def deletePoint(self, point):
        self.bounds.remove(point)
        self.updatePoints()
    def checkboxCheckChange(self):
        if self.ui.checkBox.isChecked():
            self.ui.marginEdit.setEnabled(True)
        else:
            self.ui.marginEdit.setEnabled(False)
if __name__ == "__main__":
    #print(QStyleFactory.keys())


    app = QApplication(sys.argv)
    #app.setStyle('windowsvista')
    
    MainWindow = QMainWindow()
    MainWindow.show()

    ui = CustomWindow()
    ui.setupUi(MainWindow)

    


    sys.exit(app.exec())
