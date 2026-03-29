import GUI
from pointlib import *
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QPolygonF
from UI_ressources import MapView
from pointlib import *

from algo import get_links_and_dist, main

SCALE = 0.1
DRAW_LINKS = False

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

        self.loadFile("waypoints_BXL.json")
        

    def loadFile(self, path):
        self.settings = loadsettings(path)
        global SCALE, ZONEMARGIN
        SCALE = self.settings["scale"]

        self.waypoints, self.noflyzones, self.BASE = loadWaypoints(path, self.settings["margin"])

    def globalUpdate(self, fileJustLoaded = False):
        self.updatePoints()
        self.updateZones()

        self.make_graph(fileJustLoaded)

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.graphicsView = MapView(parent=self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(290, 10, 421, 481))
        self.graphicsView.setObjectName("graphicsView")

        self.startButton.clicked.connect(self.startSim)
        self.zoneMargin.textEdited.connect(self.margin_text_changed)

        self.actionLoad_project.triggered.connect(self.loadProject)
        self.globalUpdate()

    def margin_text_changed(self,text):
        try:
            text = int(text)
            global ZONEMARGIN
            ZONEMARGIN = text
            for zone in self.noflyzones:
                zone.margin = text
            self.make_graph()
        except:
            print(f"Margin text input is not the right type, ignoring till correct")
        

    def loadProject(self,_):
        fname = QFileDialog.getOpenFileName(None, "Open File", ".", "Json files (*.json);; All files (*)")
        self.loadFile(fname[0])
        self.globalUpdate(True)

    def saveProject(self):
        fname = QFileDialog.getSaveFileName(None, "Save File", ".", "Json files (*.json);; All files (*)")

    def startSim(self):
        global ZONEMARGIN, BATTERY_ENERGY,MAX_PAYLOAD,CRUISE_ALTITUDE,SAFETY_RESERVE,CD,RHO,KANTELHOEK,A,MAXLIFT
        ZONEMARGIN = float(self.zoneMargin.text())

        EMPTY_MASS = float(self.emptyMass.text())  # kg
        BATTERY_ENERGY = float(self.batteryCap.text()) * 3600  #multiply Wh by 3600 to get the energy in Joules
        MAX_PAYLOAD = float(self.maxPayload.text())

        # --- Flight profile ---
        CRUISE_ALTITUDE = float(self.cruiseAlt.text())
        SAFETY_RESERVE = float(self.safetyMargin.text())

        # --- needed for acceleration calculations etc in mathematics.py---
        CD = float(self.cd.text())
        RHO = float(self.rho.text())
        KANTELHOEK = float(self.kantelhoek.text())
        A = float(self.area.text())

        MAXLIFT = float(self.maxLift.text())
        
        main_route, r1,r2 = main(all_waypoints=self.waypoints, noflyzones_=self.noflyzones, BASE=self.BASE)
        self.draw_routes((r1, r2))

    def addPoint(self, waypoint):
        self.waypoints.append(waypoint)
        self.updatePointIndexes()
        self.updatePoints()
        self.make_graph()

    def deletePoint(self, waypoint):
        self.waypoints.remove(waypoint)
        self.updatePointIndexes()
        self.updatePoints()
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
            widget.setStyleSheet("#waypointwidget {\n"
"border: 1px solid rgb(182, 184, 195);\n"
"background-color: qlineargradient(spread:pad, x1:0.0400505, y1:1, x2:0.672, y2:0.0738636, stop:0 rgba(205, 205, 205, 255), stop:1 rgba(238, 238, 238, 255))\n"
"}")
            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText(point.name)

            gearButton = QtWidgets.QPushButton(parent=widget)
            gearButton.setGeometry(QtCore.QRect(170, 0, 31, widget_height))
            gearButton.setText("")
            gearButton.clicked.connect(self.updatePoints)
            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 31, widget_height))
            deleteButton.setText("X")
            deleteButton.clicked.connect(lambda _, p=point: self.deletePoint(p))       #clicked.connect automatically gives only one bool as arg to the function, but you can give extra arguments if you use the lambda function (the lambda will get the bool and you can pass whatever you'd like)
            icon = QtGui.QIcon()                                                       # i also used this weird p=point to get the current value of point. if you just pass point to deletePoint the latest point value (so the last one of the for loop) will apply to all buttons!
            icon.addPixmap(QtGui.QPixmap("gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
            gearButton.setIcon(icon)

            y+=31
            widget.show()       #else they don't swot up after a second update
        self.waypointsFrame.setGeometry(QtCore.QRect(0, 0, 241, y))
        self.scrollAreaWidgetContents.setMinimumSize(QtCore.QSize(0, y))

    def updateZones(self):
        for child in self.noflyzonesFrame.children():
            child.deleteLater()

        y = 0
        for zone in self.noflyzones:
            widget_height = 31
            widget = QtWidgets.QWidget(parent=self.noflyzonesFrame)
            widget.setGeometry(QtCore.QRect(0, y, 225, widget_height))
            widget.setMinimumHeight(widget_height)

            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText(zone.name)

            gearButton = QtWidgets.QPushButton(parent=widget)
            gearButton.setGeometry(QtCore.QRect(170, 0, 31, widget_height))
            gearButton.setText("")
            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 31, widget_height))
            deleteButton.setText("X")

            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
            gearButton.setIcon(icon)

            y+=31
        self.noflyzonesFrame.setGeometry(QtCore.QRect(0, 0, 241, y))
        self.scrollAreaWidgetContents_2.setMinimumSize(QtCore.QSize(0, y))


    def make_graph(self, fileJustLoaded = False):
        self.graphicsView.clear()
        # -----------------------------
        # map background
        # -----------------------------

        # optional map image
        # self.graphicsView.draw_background("map.png")

        # -----------------------------
        # no-fly zones
        # -----------------------------
        
        # draw zones
        for zone in self.noflyzones:
            self.graphicsView.draw_zone(zone.margin_zone, scale=SCALE, text=False)
            self.graphicsView.draw_zone(zone, color= QColor(0,255,0), scale=SCALE)

        links_matrix, _ = get_links_and_dist(self.waypoints,self.noflyzones)
        n = len(links_matrix)

        if DRAW_LINKS:
            # draw links
            for i in range(n):
            #only iterating for the upper triangle of the matrix (and doing the lower at the same time)
                for j in range(i+1,n):      #i+1 for skipping the diagonal
                    self.graphicsView.draw_path(links_matrix[i][j].path, scale=SCALE)

        for point in self.waypoints:
            self.graphicsView.draw_point(point, QColor("blue"), 8,text=True,scale=SCALE)

        self.graphicsView.draw_point(self.BASE, QColor("orange"), 8,scale=SCALE)

        #self.graphicsView.fitInView(self.graphicsView.scene_.itemsBoundingRect())

        if fileJustLoaded:
            #resets transform (scroll) & cursor
            #self.graphicsView.resetTransform()
            self.graphicsView.ensureVisible(0, 0, 0, 0)  # optional

    def draw_route(self, route, color = QColor(0, 0, 200)):
        for link in route:
            self.graphicsView.draw_path(link.path, color=color,scale=SCALE)
    
    def draw_routes(self, routes):
        colors = [QColor(0,200,200), QColor(200,200,200), QColor(200,200,0), QColor(200,0,200),QColor(100,200,100)]
        color_index = 0
        for route in routes:
            self.draw_route(route,color=colors[color_index%(len(colors)-1)])
            color_index += 1
       


if __name__ == "__main__":
    #print(QStyleFactory.keys())


    app = QApplication(sys.argv)
    #app.setStyle('windowsvista')
    
    MainWindow = QMainWindow()
    MainWindow.show()

    ui = CustomWindow()
    ui.setupUi(MainWindow)

    


    sys.exit(app.exec())
