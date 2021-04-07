import sys
import pickle
import numpy as np
from platform import system
from time import time
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QTimer, QAbstractTableModel, Qt
from PyQt5.QtWidgets import QMainWindow, QApplication, QOpenGLWidget, QMessageBox
from PyQt5.uic import loadUi
from OpenGL.arrays import numpymodule
numpymodule.NumpyHandler.ERROR_ON_COPY = True

TURN_ANGLE = 4.0
MOVE = 10
TIME = 0.001
GRAVITY = 1000
HEADER = ["Name", "Mass", "PosX", "PosY", "PosZ", "VelX", "VelY", "VelZ"]
MAX_TRACE = 100
FPSCount = []


# Planets
class Planet:
    index = 1

    def __init__(self, name=None, mass=None, pos=None, vel=None, color=None):
        self.name = name if name is not None else "p" + str(Planet.index)
        Planet.index += 1
        self.mass = mass if mass is not None else np.random.rand() * 1000
        self.pos = pos if pos is not None else np.random.rand(3) * 2000 - 1000
        self.vel = vel if vel is not None else np.random.rand(3) * 500 - 250
        self.color = color if color is not None else np.random.rand(3)
        self.radius = self.mass / 20
        self.trace = [None] * MAX_TRACE
        self.currentTraceIndex = -1

    def paintPlanet(self, usePoint, showTail):
        if usePoint:
            glDisable(GL_LIGHTING)
            glColor3f(*self.color)
            glPointSize(10)
            glBegin(GL_POINTS)
            glVertex3f(*self.pos)
            glEnd()
            glEnable(GL_LIGHTING)
        else:
            glPushMatrix()
            glTranslatef(*self.pos)
            glColor3f(*self.color)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, list(self.color) + [0.0])
            glutSolidSphere(self.radius, 20, 15)  # This line generates NullFunction Error in Windows 10
            glPopMatrix()

        if showTail:
            # Paint trace.
            glDisable(GL_LIGHTING)
            glBegin(GL_LINE_STRIP)
            for i in range(self.currentTraceIndex + 1, MAX_TRACE):
                if self.trace[i] is not None:
                    glVertex3f(*self.trace[i])
            for i in range(self.currentTraceIndex + 1):
                if self.trace[i] is not None:
                    glVertex3f(*self.trace[i])
            glEnd()
            glEnable(GL_LIGHTING)

    def toList(self):
        return [self.name, self.mass,
                self.pos[0], self.pos[1], self.pos[2],
                self.vel[0], self.vel[1], self.vel[2]]

    def updateTrace(self):
        self.currentTraceIndex = (self.currentTraceIndex + 1) % MAX_TRACE
        self.trace[self.currentTraceIndex] = np.copy(self.pos)


# Create Planets Table in the main GUI window
class PlanetsTable(QAbstractTableModel):
    def __init__(self, planets=None):
        super(PlanetsTable, self).__init__()
        p1 = Planet("p1", 20, np.array([100, 0, 0]), np.array([0, 5, 0]), np.array([1, 0, 0]))
        p2 = Planet("p2", 10, np.array([0, 0, 0]), np.array([0, -10, 0]), np.array([0, 1, 0]))
        p3 = Planet("p3", 10, np.array([100, 0, 100]), np.array([0, 0, 3]), np.array([0, 0, 1]))
        self.planets = [p1, p2, p3]

    def data(self, index, role):
        if role == Qt.DisplayRole:
            ret = self.planets[index.row()].toList()[index.column()]
            return ret if index.column() == 0 else "%.4f" % ret
        if role == Qt.DecorationRole and index.column() == 0:
            return QColor.fromRgb(*(self.planets[index.row()].color * 255).astype(int))

    def rowCount(self, index):
        return len(self.planets)

    def columnCount(self, index):
        return len(HEADER)

    def headerData(self, index, rowOrCol, role):
        if role == Qt.DisplayRole:
            if rowOrCol == Qt.Horizontal:
                return HEADER[index]
            elif rowOrCol == Qt.Vertical:
                return index + 1

    def addPlanet(self, planet):
        self.planets.append(planet)

    def simulate(self, adjustment, iteration):
        # We use matrix to accelerate calculation.
        count = len(self.planets)
        pos = np.zeros(shape=(count, 3))
        vel = np.zeros(shape=(count, 3))
        mass = np.zeros(shape=(count, 1))
        for i in range(count):
            pos[i, :] = self.planets[i].pos
            vel[i] = self.planets[i].vel
            mass[i] = self.planets[i].mass

        for _ in range(iteration):
            # Calculate acceleration
            x = pos[:, 0: 1]  # To preserve matrix shape, i.e. we want a column vector.
            y = pos[:, 1: 2]
            z = pos[:, 2: 3]

            # These steps consume a lot of time. This is an O(n^2) algorithm.
            dx = x.T - x
            dy = y.T - y
            dz = z.T - z

            # 1e-10 to prevent ZeroDivisionError, as distance between a planet and itself is always zero.
            inv_r3 = (dx ** 2 + dy ** 2 + dz ** 2 + 1e-10) ** (-1.5)

            ax = adjustment * GRAVITY * (dx * inv_r3) @ mass
            ay = adjustment * GRAVITY * (dy * inv_r3) @ mass
            az = adjustment * GRAVITY * (dz * inv_r3) @ mass

            acc = np.hstack((ax, ay, az))

            # Calculate velocity.
            vel += acc * TIME

            # Calculate position.
            pos += vel * TIME

        # Copy data back
        for i in range(count):
            self.planets[i].pos = pos[i]
            self.planets[i].vel = vel[i]

        # Update tail.
        for planet in self.planets:
            planet.updateTrace()

        # Update table view
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(len(self.planets) - 1, len(self.planets[0].toList()) - 1))

    def setData(self, index, value, role):
        row = index.row()
        col = index.column()
        if col == 0:
            self.planets[row].name = value
            self.dataChanged.emit(index, index)
            return True
        else:
            # First, check it's a valid input
            try:
                value = float(value)
                if col == 1:
                    self.planets[row].mass = value
                    self.planets[row].radius = value / 20
                elif col == 2:
                    self.planets[row].pos[0] = value
                elif col == 3:
                    self.planets[row].pos[1] = value
                elif col == 4:
                    self.planets[row].pos[2] = value
                elif col == 5:
                    self.planets[row].vel[0] = value
                elif col == 6:
                    self.planets[row].vel[1] = value
                elif col == 7:
                    self.planets[row].vel[2] = value

                self.dataChanged.emit(index, index)
                return True
            except ValueError:
                return False

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsSelectable

    def destroyPlanets(self):
        # Formula learnt from https://wenku.baidu.com/view/ed88f4bcfab069dc51220129.html#
        # The line is known to be x = t, y = t, z = t (Parametric equation).
        count = len(self.planets)
        pos = np.zeros(shape=(count, 3))
        radius = np.zeros(shape=count)
        for i in range(count):
            pos[i, :] = self.planets[i].pos
            radius[i] = self.planets[i].radius

        temp1 = pos / 3
        temp2 = temp1.copy()
        temp3 = temp1.copy()

        temp1[:, 0] *= 2
        temp1[:, 1] *= -1
        temp1[:, 2] *= -1

        temp2[:, 0] *= -1
        temp2[:, 1] *= 2
        temp2[:, 2] *= -1

        temp3[:, 0] *= -1
        temp3[:, 1] *= -1
        temp3[:, 2] *= 2

        distances = np.sqrt(np.square(temp1.sum(axis=1)) + np.square(temp2.sum(axis=1)) + np.square(temp3.sum(axis=1)))
        destroyed = distances < radius
        for planet in np.where(destroyed == True)[0]:
            del self.planets[planet]
        self.layoutChanged.emit()


# Create OpenGL Widget in the main GUI window
class OpenGLWidget(QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super(OpenGLWidget, self).__init__(*args, **kwargs)
        # Enable responds to keyboard.
        self.setFocusPolicy(Qt.StrongFocus)
        self.camera = {"eye": np.array([0, 0, 50], np.float64),
                       "center": np.array([0.0, 0.0, 0.0], np.float64),
                       "up": np.array([0.0, 1.0, 0.0], np.float64),
                       "lon": -180,
                       "lat": 0.0}
        self.showAxes = True
        self.showShadingTest = False  # To show I have correct lighting and hidden surface removal.
        self.r = 0
        self.usePoint = True
        self.deathStarWorking = False
        self.showTail = False

    def initializeGL(self):
        # glutInit() is a system dependent function in PyQt5 framework.
        # We don't neet to, and should not call it in MACOS.
        # And all glut functions in Windows will cause OpenGL.error.NullFunctionError.
        if system() == "Linux":
            glutInit()

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60, 1, 0.1, 5000)
        glMatrixMode(GL_MODELVIEW)

    def drawAxes():
        glBegin(GL_LINES)
        # Red X.
        glColor3f(1.0, 0.0, 0.0)
        glVertex3d(10000, 0.0, 0.0)
        glVertex3d(0.0, 0.0, 0.0)

        # White Y.
        glColor3f(1.0, 1.0, 1.0)
        glVertex3d(0.0, 10000, 0.0)
        glVertex3d(0.0, 0.0, 0.0)

        # Blue Z.
        glColor3f(0.078, 0.835, 0.96)
        glVertex3d(0.0, 0.0, 10000)
        glVertex3d(0.0, 0.0, 0.0)
        glEnd()
        # print("drawAxes")

    def calculateLookAtPoint(self):
        eye = self.camera["eye"]
        lon = self.camera["lon"]
        lat = self.camera["lat"]
        self.camera["center"][0] = eye[0] + np.cos(np.radians(lat)) * np.sin(np.radians(lon))
        self.camera["center"][1] = eye[1] + np.sin(np.radians(lat))
        self.camera["center"][2] = eye[2] + np.cos(np.radians(lat)) * np.cos(np.radians(lon))

    def paintGL(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        self.calculateLookAtPoint()
        eye = self.camera["eye"]
        center = self.camera["center"]
        up = self.camera["up"]
        gluLookAt(eye[0], eye[1], eye[2], center[0], center[1], center[2], up[0], up[1], up[2])

        glDisable(GL_LIGHTING)
        if self.showAxes:
            OpenGLWidget.drawAxes()

        if self.deathStarWorking:
            glBegin(GL_LINES)
            glColor(0.0, 1.0, 0.0)
            glVertex3d(10000, 10000, 10000)
            glVertex3d(-10000, -10000, -10000)
            glEnd()
            self.planetsTable.destroyPlanets()

        glEnable(GL_LIGHTING)
        glShadeModel(GL_SMOOTH)

        for planet in self.planetsTable.planets:
            planet.paintPlanet(self.usePoint, self.showTail)

        if self.showShadingTest:
            glColor3f(1.0, 0.0, 0.0)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, list(np.array([1.0, 0.0, 0.0])) + [0.0])
            glutSolidCube(1.0)
            glRotatef(self.r * 2.0, 0, 1, 0)
            glTranslatef(0.0, 0.0, 1.0)
            glRotatef(self.r, 1, 0, 0)
            glRotatef(self.r, 0, 1, 0)
            glRotatef(self.r, 0, 0, 1)
            glColor3f(0.0, 1.0, 0.0)
            glMaterialfv(GL_FRONT, GL_DIFFUSE, list(np.array([0.0, 1.0, 0.0])) + [0.0])
            glutSolidSphere(0.5, 20, 15)

    def keyPressEvent(self, k):
        key = k.key()
        if key == 65:  # 'a'
            self.showAxes = not self.showAxes
        elif key == 16777234:  # 'left arrow'
            self.camera["lon"] += TURN_ANGLE
        elif key == 16777236:  # 'right arrow'
            self.camera["lon"] -= TURN_ANGLE
        elif key == 16777235:  # 'up arrow'
            if self.camera["lat"] + TURN_ANGLE < 90:
                self.camera["lat"] += TURN_ANGLE
        elif key == 16777237:  # 'down arrow'
            if self.camera["lat"] - TURN_ANGLE > -90:
                self.camera["lat"] -= TURN_ANGLE
        elif key == 85:  # 'u'
            self.camera["eye"][1] += MOVE
            self.camera["center"][1] += MOVE
        elif key == 68:  # 'd'
            self.camera["eye"][1] -= MOVE
            self.camera["center"][1] -= MOVE
        elif key == 66:  # 'b'
            lon = self.camera["lon"]
            lat = self.camera["lat"]
            self.camera["eye"][0] -= MOVE * np.sin(np.radians(lon))
            self.camera["eye"][1] -= MOVE * np.sin(np.radians(lat))
            self.camera["eye"][2] -= MOVE * np.cos(np.radians(lon))
        elif key == 70:  # 'f'
            lon = self.camera["lon"]
            lat = self.camera["lat"]
            self.camera["eye"][0] += MOVE * np.sin(np.radians(lon))
            self.camera["eye"][1] += MOVE * np.sin(np.radians(lat))
            self.camera["eye"][2] += MOVE * np.cos(np.radians(lon))
        elif key == 76:  # 'l'
            lon = self.camera["lon"]
            self.camera["eye"][0] += MOVE * np.sin(np.radians(lon + 90))
            self.camera["eye"][2] += MOVE * np.cos(np.radians(lon + 90))
        elif key == 82:  # 'r'
            lon = self.camera["lon"]
            self.camera["eye"][0] += MOVE * np.sin(np.radians(lon - 90))
            self.camera["eye"][2] += MOVE * np.cos(np.radians(lon - 90))
        elif key == 84:  # 't'
            self.showTail = not self.showTail
        elif key == 83: # 's'
            self.showShadingTest = not self.showShadingTest
        elif key == 80:  # 'p'
            self.usePoint = not self.usePoint
        elif key == 75:  # 'k'
            self.deathStarWorking = not self.deathStarWorking
        else:
            print("NOT IMPLEMENTED:", key)

    def cameraToString(self):
        return "(%d, %d, %d, %d, %d)" % (self.camera["eye"][0], self.camera["eye"][1], self.camera["eye"][2],
                                         self.camera["lat"], self.camera["lon"])

# Create the main GUI window.
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi("main.ui", self)
        # For statistics.
        self.frameStart = time()
        self.frameEnd = 0

        # Run button.
        self.running = False
        self.runButton.toggled.connect(self.runButtonClicked)

        # Add button.
        self.addButton.clicked.connect(self.addButtonClicked)

        # Remove button.
        self.removeButton.clicked.connect(self.removeButtonClicked)

        # Save menu.
        self.actionSave.triggered.connect(self.save)

        # Load menu.
        self.actionLoad.triggered.connect(self.load)

        # Help menu.
        self.actionShow_Help.triggered.connect(self.help)

        # Calculate Average FPS menu.
        self.actionCalculate_Ave_FPS.triggered.connect(self.calculateAveFPS)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.redrawOpenGL)
        self.timer.setInterval(1000 // 60)
        self.timer.start()

        # Planets table.
        self.planetsTable = PlanetsTable()
        self.openGLWidget.planetsTable = self.planetsTable
        self.planetsView.setModel(self.planetsTable)

    def calculateAveFPS(self):
        global FPSCount
        averageFPS = np.mean(FPSCount)
        print(averageFPS, "GL_POINTS" if self.openGLWidget.usePoint else "Solid Sphere with Light", ("On" if self.openGLWidget.showTail else "Off"))
        data = None

        # Write it to a file.
        try:
            with open("statistics.pkl", "rb") as file:
                data = pickle.load(file)
        except (EOFError, FileNotFoundError):
            data = []

        data.append((len(self.planetsTable.planets), self.openGLWidget.usePoint,
                     self.openGLWidget.showTail, averageFPS))
        try:
            with open("statistics.pkl", "wb") as file:
                pickle.dump(data, file)
        except Error as e:
            print(e)
        FPSCount = []

    def runButtonClicked(self, state):
        self.running = state

    def addButtonClicked(self):
        self.planetsTable.addPlanet(Planet())
        self.planetsTable.layoutChanged.emit()

    def removeButtonClicked(self):
        try:
            del self.planetsTable.planets[self.planetsView.selectedIndexes()[0].row()]
            self.planetsTable.layoutChanged.emit()
        except IndexError:
            pass

    def save(self):
        try:
            with open("planets.pkl", "wb") as file:
                pickle.dump(self.planetsTable.planets, file)
        except Error as e:
            print(e)

    def load(self):
        try:
            with open("planets.pkl", "rb") as file:
                self.planetsTable.planets = pickle.load(file)
            self.planetsTable.layoutChanged.emit()
        except Exception as e:
            print(e)

    def help(self):
        msg = QMessageBox()
        msg.setWindowTitle("Help")
        msg.setText("How to use this Particle System?")
        msg.setInformativeText("Use arrow keys to change looking direction.\n"
                               "Use \"d\" to to down.\n"
                               "Use \"u\" to go up.\n"
                               "Use \"f\" to go forward.\n"
                               "Use \"b\" to go back.\n"
                               "Use \"r\" to go right.\n"
                               "Use \"l\" to fo left.\n"
                               "Use \"a\" to toggle on/off axes.\n"
                               "Use \"s\" to toggle on/off shading test.\n"
                               "Use \"t\" to toggle on/off planet trace.\n"
                               "Use \"p\" to toggle on/off shading.\n"
                               "A Death Star hides somewhere in this universe, use \"k\" to active it and kill planets.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def redrawOpenGL(self):
        if self.running and len(self.planetsTable.planets) > 0:
            self.planetsTable.simulate(self.gravitySlider.value() / 10, self.speedSlider.value())

        if self.openGLWidget.showShadingTest:
            self.openGLWidget.r += 1.0

        self.openGLWidget.repaint()

        # Calculate true FPS.
        try:
            self.frameEnd = time()
            difference = self.frameEnd - self.frameStart
            fps = 1 / difference
            # To prevent too fast flashing.
            if np.random.rand() > 0.6:
                self.fpsLabel.setText("FPS: " + "%.4f" % fps)
                self.tpsLabel.setText("Time Per Frame: " + "%.4f" % difference + "s")
                if self.running:
                    FPSCount.append(fps)
            self.frameStart = self.frameEnd
        except ZeroDivisionError:
            # This only happens in Windows, wired.
            pass

        # Some trivial info.
        self.planetsCountLabel.setText("Planets Count: " + str(len(self.planetsTable.planets)))
        self.eyePosLatLonLabel.setText("Eye Pos Lat Lon: " + self.openGLWidget.cameraToString())
        self.shadingTestLabel.setText("Shading Test: " + ("On" if self.openGLWidget.showShadingTest else "Off"))
        self.deathStarLabel.setText("Death Star: " + ("On" if self.openGLWidget.deathStarWorking else "Off"))
        self.renderLabel.setText("Render: " + ("GL_POINTS" if self.openGLWidget.usePoint else "Solid Sphere with Light"))
        self.axesLabel.setText("Axes: " + ("On" if self.openGLWidget.showAxes else "Off"))
        self.tailLabel.setText("Tail: " + ("On" if self.openGLWidget.showTail else "Off"))


# Create the application and execute it.
def main():
    app = QApplication(sys.argv)
    # Get rid of ugly old Windows 98 style.
    app.setStyle("Fusion")
    mainWindow = MainWindow()
    mainWindow.show()
    app.exec_()


if __name__ == "__main__":
    main()

