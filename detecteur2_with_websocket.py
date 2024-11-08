
import cv2
import numpy as np
import tkinter as tk
import json  # Import json to handle file saving
from flask import Flask, jsonify
from flask_socketio import SocketIO, emit  # Import SocketIO for WebSocket communication
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# Paramètres de détection de mouvement
kernel_blur = 5
seuil = 15
surface = 5000

# Initialisation de la capture vidéo
cap = cv2.VideoCapture(0)

ret, originale = cap.read()
originale = cv2.cvtColor(originale, cv2.COLOR_BGR2GRAY)
originale = cv2.GaussianBlur(originale, (kernel_blur, kernel_blur), 0)
kernel_dilate = np.ones((5, 5), np.uint8)

# Interface Tkinter
root = tk.Tk()
root.title("Suivi de la trajectoire d'un objet")

# Variables pour stocker les coordonnées
x_coords, y_coords = [], []

# Création d'une figure pour afficher la trajectoire
fig, ax = plt.subplots()
ax.set_xlim(0, 640)
ax.set_ylim(0, 480)
line, = ax.plot([], [], 'bo-', markersize=5)  # Point initial et ligne entre les points

# Chemin du fichier JSON
json_file_path = "coordinates.json"

# Fonction pour sauvegarder les coordonnées dans un fichier JSON
def save_coordinates_to_json(x, y):
    data = {"x": x, "y": y}
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file)

# Fonction pour obtenir les coordonnées de l'objet en mouvement
def get_object_coordinates():
    global cap, originale, x_coords, y_coords

    ret, frame = cap.read()
    if not ret:
        return None, None

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (kernel_blur, kernel_blur), 0)

    delta = cv2.absdiff(originale, gray)
    delta = cv2.threshold(delta, seuil, 255, cv2.THRESH_BINARY)[1]
    delta = cv2.dilate(delta, kernel_dilate, iterations=3)

    contours, _ = cv2.findContours(delta, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    frame_contour=frame.copy()

    for contour in contours:
        
        if cv2.contourArea(contour) < surface:
            continue

        x, y, w, h = cv2.boundingRect(contour)
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 0, 255), 2)
        cv2.imshow("frame", frame)
        originale=gray
        cx, cy = x + w // 2, y + h // 2  # Coordonnées du centre de l'objet
        x_coords.append(cx)
        y_coords.append(cy)

        # Enregistrement dans le fichier JSON
        save_coordinates_to_json(x_coords, y_coords)

        # Émission des coordonnées via WebSocket
        socketio.emit('new_coordinates', {'x': cx, 'y': cy})

        return cx, cy
    return None, None

# Fonction d'animation pour mettre à jour la trajectoire
def update_trajectory(i):
    cx, cy = get_object_coordinates()
    if cx is not None and cy is not None:
        line.set_data(x_coords, y_coords)
    return line,

# Configuration de l'animation
ani = FuncAnimation(fig, update_trajectory, blit=True)

# Création de l'application Flask
app = Flask(__name__)
socketio = SocketIO(app)  # Initialisation de SocketIO

# Route pour récupérer les coordonnées JSON
@app.route('/coordinates', methods=['GET'])
def get_coordinates():
    try:
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "No coordinates found"}), 404

# Fonction principale pour démarrer Flask-SocketIO et Tkinter
def main():
    # Exécution du serveur SocketIO dans un thread séparé
    from threading import Thread
    socketio_thread = Thread(target=lambda: socketio.run(app, host="192.168.1.1",port=8000,debug=True, use_reloader=False))
    socketio_thread.start()

    # Affichage Tkinter
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack()
    tk.mainloop()

    # Libération des ressources de capture vidéo
    #cap.release()
    #cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
