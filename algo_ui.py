import GUI
from pointlib import *
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QPolygonF
from UI_ressources import MapView
from pointlib import *

from algo import get_links_and_dist, main

SCALE = 5
DRAW_LINKS = False

class CustomWindow(GUI.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        
        self.waypoints = []
        self.BASE = None
        self.noflyzones = []

        self.waypoints, self.noflyzones, self.BASE = loadWaypoints("waypoints.json")
        

    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.graphicsView = MapView(parent=self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(290, 10, 421, 481))
        self.graphicsView.setObjectName("graphicsView")

        self.startButton.clicked.connect(self.startSim)
        self.updatePoints()
        self.updateZones()

        self.make_graph()

    def startSim(self):
        global ZONEMARGIN,EMPTY_MASS,BATTERY_ENERGY,MAX_PAYLOAD,CRUISE_ALTITUDE,SAFETY_RESERVE,CD,RHO,KANTELHOEK,A,MAXLIFT
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

        main_route, r1,r2 = main()
        self.draw_routes((r1, r2))

    def addPoint(self, waypoint):
        self.waypoints.append(waypoint)
        self.updatePoints()

    def deletePoint(self, waypoint):
        point = self.sender()
        print(point)
        #self.waypoints.remove(waypoint)
        #self.updatePoints()

    def updatePoints(self):
        for child in self.waypointsFrame.children():
            child.deleteLater()

        y = 0
        for point in self.waypoints:
            widget_height = 31
            widget = QtWidgets.QWidget(parent=self.waypointsFrame)
            widget.setGeometry(QtCore.QRect(0, y, 241, widget_height))
            widget.setMinimumHeight(widget_height)

            label = QtWidgets.QLabel(parent=widget)
            label.setGeometry(QtCore.QRect(5, 5, 131, 21))
            label.setText(point.name)

            gearButton = QtWidgets.QPushButton(parent=widget)
            gearButton.setGeometry(QtCore.QRect(170, 0, 31, widget_height))
            gearButton.setText("")
            deleteButton = QtWidgets.QPushButton(parent=widget)
            deleteButton.setGeometry(QtCore.QRect(195, 0, 31, widget_height))
            deleteButton.setText("X")
            deleteButton.clicked.connect(self.deletePoint)
            icon = QtGui.QIcon()
            icon.addPixmap(QtGui.QPixmap("gear.png"), QtGui.QIcon.Mode.Normal, QtGui.QIcon.State.On)
            gearButton.setIcon(icon)

            y+=31
        self.waypointsFrame.setGeometry(QtCore.QRect(0, 0, 241, y))
        self.scrollAreaWidgetContents.setMinimumSize(QtCore.QSize(0, y))

    def updateZones(self):
        for child in self.noflyzonesFrame.children():
            child.deleteLater()

        y = 0
        for zone in self.noflyzones:
            widget_height = 31
            widget = QtWidgets.QWidget(parent=self.noflyzonesFrame)
            widget.setGeometry(QtCore.QRect(0, y, 241, widget_height))
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


    def make_graph(self):

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
            self.graphicsView.draw_zone(zone.inflated(2), scale=SCALE, text=False)
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
