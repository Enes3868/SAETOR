import sys
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QHBoxLayout, QVBoxLayout

app = QApplication(sys.argv)
root = QWidget()
root.resize(500, 250)
root.setWindowTitle("Une première fenêtre")
grid = QHBoxLayout()

def appui_bouton():
    nom = QLabel(f"{edit.text()}")
    layout.addWidget(nom)
    layout.addWidget(exit)

def quitte_bouton():
    sys.exit()

label = QLabel("Quel est votre nom :")
edit = QLineEdit()
bouton = QPushButton("ok")
bouton.clicked.connect(appui_bouton)
exit = QPushButton("Quitte")
exit.clicked.connect(quitte_bouton)

layout = QVBoxLayout()
layout.addWidget(label)
layout.addWidget(edit)
layout.addWidget(bouton)
layout.addWidget(exit)
root.setLayout(layout)
root.show()

if __name__ == '__main__':
    sys.exit(app.exec())