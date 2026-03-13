import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene
)
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QPolygonF
)
from PyQt6.QtCore import Qt, QPointF

from pointlib import *
import GUI

class MapView(QGraphicsView):

    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        self.setRenderHint(self.renderHints().Antialiasing)

        # enable panning
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    # zoom
    def wheelEvent(self, event):
        zoom = 1.2
        if event.angleDelta().y() > 0:
            self.scale(zoom, zoom)
        else:
            self.scale(1/zoom, 1/zoom)

    # -----------------------------
    # DRAW FUNCTIONS
    # -----------------------------

    def draw_background(self, image_path):
        pixmap = QPixmap(image_path)
        self.scene.addPixmap(pixmap)

    def draw_point(self, point, color=QColor("blue"), size=2):
        r = size / 2
        self.scene.addEllipse(
            point.x - r,
            point.y - r,
            size,
            size,
            QPen(color),
            QBrush(color)
        )

    def draw_zone(self, zone):
        polygon = QPolygonF([QPointF(p.x, p.y) for p in zone.bounds])

        pen = QPen(QColor(200, 0, 0))
        brush = QBrush(QColor(255, 0, 0, 80))

        self.scene.addPolygon(polygon, pen, brush)

    def draw_graph(self, graph):
        pen = QPen(QColor(150, 150, 150))
        pen.setWidth(1)

        for node, edges in graph.items():
            self.draw_point(node,size=1)
            for neigh, _ in edges:
                self.scene.addLine(
                    node.x, node.y,
                    neigh.x, neigh.y,
                    pen
                )

    def draw_path(self, path):
        pen = QPen(QColor(0, 200, 0))
        pen.setWidth(1)

        for i in range(len(path)-1):
            a = path[i]
            b = path[i+1]
            self.draw_point(b, color=QColor(0, 200, 0), size=1)
            self.scene.addLine(
                a.x, a.y,
                b.x, b.y,
                pen
            )


class CustomWindow(GUI.Ui_MainWindow):
    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
    def build_demo(self):

        # -----------------------------
        # demo map background
        # -----------------------------

        # optional map image
        # self.graphicsView.draw_background("map.png")

        # -----------------------------
        # no-fly zones
        # -----------------------------

        nofly = [
            NoFlyZone([
                Point(10,20,"xy"),
                Point(20,20,"xy"),
                Point(20,10,"xy"),
                Point(10,10,"xy")
            ]),
            NoFlyZone([
                Point(5,7,"xy"),
                Point(40,7,"xy"),
                Point(40,3,"xy"),
                Point(5,3,"xy")
            ])
        ]

        for zone in nofly:
            self.graphicsView.draw_zone(zone)

        # -----------------------------
        # start / goal
        # -----------------------------

        start = WayPoint(16,30,coord_type="xy")
        goal = WayPoint(15,-6,coord_type="xy")

        # -----------------------------
        # path planning
        # -----------------------------

        margin = 2
        inflated = [z.inflated(margin) for z in nofly]

        nodes = collect_nodes(start, goal, inflated)
        graph = build_visibility_graph(nodes, inflated)

        link = Link(start, goal, nofly)

        # optional visibility graph
        #self.graphicsView.draw_graph(graph)

        # shortest path
        self.graphicsView.draw_path(link.path)

        
        self.graphicsView.draw_point(start, QColor("blue"), 8)
        self.graphicsView.draw_point(goal, QColor("orange"), 8)