import GUI
from pointlib import *
from PyQt6 import QtWidgets, QtCore
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtGui import QPixmap, QPen, QBrush, QColor, QPolygonF
from UI_ressources import MapView
from pointlib import *

from algo import get_links_and_dist, main

SCALE = 5

class CustomWindow(GUI.Ui_MainWindow):
    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.graphicsView = MapView(parent=self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(290, 10, 421, 481))
        self.graphicsView.setObjectName("graphicsView")

    def build_demo(self):

        # -----------------------------
        # demo map background
        # -----------------------------

        # optional map image
        # self.graphicsView.draw_background("map.png")

        # -----------------------------
        # no-fly zones
        # -----------------------------


        waypoints, nofly, BASE = loadWaypoints("waypoints.json")

        # draw zones
        for zone in nofly:
            self.graphicsView.draw_zone(zone.inflated(2), scale=SCALE)
            self.graphicsView.draw_zone(zone, color= QColor(0,255,0), scale=SCALE)

        links_matrix, _ = get_links_and_dist(waypoints,nofly)
        n = len(links_matrix)
        # draw links
        """for i in range(n):
        #only iterating for the upper triangle of the matrix (and doing the lower at the same time)
            for j in range(i+1,n):      #i+1 for skipping the diagonal
                self.graphicsView.draw_path(links_matrix[i][j].path, scale=SCALE)
"""
        for point in waypoints:
            self.graphicsView.draw_point(point, QColor("blue"), 8,text=True,scale=SCALE)

        self.graphicsView.draw_point(BASE, QColor("orange"), 8,scale=SCALE)

        #self.graphicsView.fitInView(self.graphicsView.scene_.itemsBoundingRect())

        main_route, r1,r2 = main()
        self.draw_route(main_route)
        #self.draw_route(r2)

    def draw_route(self, route):
        for link in route:
            self.graphicsView.draw_path(link.path, color=QColor(0, 0, 200),scale=SCALE)

       


if __name__ == "__main__":
    #print(QStyleFactory.keys())


    app = QApplication(sys.argv)
    #app.setStyle('windowsvista')
    
    MainWindow = QMainWindow()
    MainWindow.show()

    ui = CustomWindow()
    ui.setupUi(MainWindow)

    ui.build_demo()

    


    sys.exit(app.exec())
