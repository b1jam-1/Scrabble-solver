from app import app
import threading
import webbrowser

if __name__ == '__main__':

    threading.Timer(1.0, lambda: webbrowser.open_new_tab('http://127.0.0.1:5000/')).start() # Ouvre automatiquement le navigateur après le démarrage du serveur
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)