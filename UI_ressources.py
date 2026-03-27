from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene
)
from PyQt6.QtGui import (
    QPixmap, QPen, QBrush, QColor, QPolygonF, QPainter
)
from PyQt6.QtCore import Qt, QPointF
import pointlib

def draw_point(scene:QGraphicsScene, point):
    r = 2
    scene.addEllipse(
        point.x - r,
        point.y - r,
        2*r,
        2*r
    )

def draw_link(scene:QGraphicsScene, link):
    for i in range(len(link.path) - 1):
        a = link.path[i]
        b = link.path[i+1]

        scene.addLine(a.x, a.y, b.x, b.y)


def draw_zone(scene:QGraphicsScene, zone):
    poly = QPolygonF([QPointF(p.x, p.y) for p in zone.bounds])
    scene.addPolygon(poly)

class MapView(QGraphicsView):

    def __init__(self, *args, grid_size = 400, **kwargs):
        super().__init__(*args, **kwargs)

        self.scene_ = QGraphicsScene()
        self.setScene(self.scene_)

        self.setRenderHint(self.renderHints().Antialiasing)

        # enable panning
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.grid_size = grid_size  # size of each cell (5x5 pixels)

    def drawBackground(self, painter: QPainter, rect):
        super().drawBackground(painter, rect)

        # Set grid appearance
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(0)  # cosmetic pen (stays thin when zooming)
        painter.setPen(pen)

        left = int(rect.left())
        right = int(rect.right())
        top = int(rect.top())
        bottom = int(rect.bottom())

        # Align grid to origin
        first_x = left - (left % self.grid_size)
        first_y = top - (top % self.grid_size)

        # Draw vertical lines
        x = first_x
        while x <= right:
            painter.drawLine(x, top, x, bottom)
            x += self.grid_size

        # Draw horizontal lines
        y = first_y
        while y <= bottom:
            painter.drawLine(left, y, right, y)
            y += self.grid_size

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
        self.scene_.addPixmap(pixmap)

    def draw_point(self, point:pointlib.Point, color=QColor("blue"), size=2, text = False, scale = 1):
        r = size / 2
        self.scene_.addEllipse(
            point.x*scale - r,
            -(point.y*scale) - r,
            size,
            size,
            QPen(color),
            QBrush(color)
        )

        if text and hasattr(point,"name"):
            text_item = self.scene_.addText(point.name)
            text_item.setPos(point.x*scale, -(point.y)*scale)
            

    def draw_zone(self, zone:pointlib.NoFlyZone, color = QColor(255,0,0), text = True, scale = 1):
        polygon = QPolygonF([QPointF(p.x*scale, -(p.y*scale)) for p in zone.bounds])

        color.setAlpha(80)
        pen = QPen(QColor(int(color.red()*0.7), int(color.green()*0.7), int(color.blue()*0.7)))
        brush = QBrush(color)

        self.scene_.addPolygon(polygon, pen, brush)
        
        if text:
            #drawing text labels
            text_scale = 0.5

            text_item = self.scene_.addText(zone.name)
            text_item.setScale(text_scale)
            # get center of polygon
            rect = polygon.boundingRect()
            center = rect.center()

            # center text around that point
            text_rect = text_item.boundingRect()
            text_item.setPos(
                center.x() - text_rect.width()*text_scale/2,
                center.y() - text_rect.height()*text_scale/2
    )

    def draw_graph(self, graph,scale = 1):
        pen = QPen(QColor(150, 150, 150))
        pen.setWidth(1)

        for node, edges in graph.items():
            self.draw_point(node,size=1, scale=scale)
            for neigh, _ in edges:
                self.scene_.addLine(
                    node.x*scale, -(node.y*scale),
                    neigh.x*scale, -(neigh.y*scale),
                    pen
                )

    def draw_path(self, path, color = QColor(0, 200, 0), scale = 1):
        pen = QPen(color)
        pen.setWidth(1)

        for i in range(len(path)-1):
            a = path[i]
            b = path[i+1]
            self.draw_point(b, color=QColor(0, 200, 0), size=1, scale=scale)
            self.scene_.addLine(
                a.x*scale, -(a.y*scale),        #flipping y coordinates cuz see earlier
                b.x*scale, -(b.y*scale),
                pen
            )