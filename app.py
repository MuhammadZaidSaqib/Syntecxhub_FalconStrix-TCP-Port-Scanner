from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_socketio import SocketIO, emit
import socket
import datetime
from concurrent.futures import ThreadPoolExecutor
import webbrowser



app = Flask(__name__)
app.config["SECRET_KEY"] = "falconstrix_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

db = SQLAlchemy(app)

# IMPORTANT: Use threading mode (NO eventlet)
socketio = SocketIO(app, async_mode="threading")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"




class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))


class ScanHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host = db.Column(db.String(100))
    port = db.Column(db.Integer)
    status = db.Column(db.String(50))
    banner = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))




def scan_port(host, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))

            if result == 0:
                banner = grab_banner(host, port)
                return port, "OPEN", banner
            else:
                return port, "CLOSED", ""
    except:
        return port, "ERROR", ""


def grab_banner(host, port):
    try:
        with socket.socket() as s:
            s.settimeout(1)
            s.connect((host, port))
            banner = s.recv(1024).decode(errors="ignore").strip()
            return banner[:150]
    except:
        return ""




@socketio.on("start_scan")
def handle_scan(data):
    print("Scan request received:", data)

    host = data["host"]
    start = int(data["start"])
    end = int(data["end"])

    total = end - start + 1
    scanned = 0

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(scan_port, host, p) for p in range(start, end + 1)]

        for future in futures:
            port, status, banner = future.result()
            scanned += 1

            history = ScanHistory(host=host, port=port, status=status, banner=banner)
            db.session.add(history)
            db.session.commit()

            progress = int((scanned / total) * 100)

            emit("scan_result", {
                "port": port,
                "status": status,
                "banner": banner,
                "progress": progress
            })




@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()
        if user and user.password == request.form["password"]:
            login_user(user)
            return redirect("/dashboard")
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/history")
@login_required
def history():
    scans = ScanHistory.query.order_by(ScanHistory.timestamp.desc()).all()
    return render_template("history.html", scans=scans)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")




if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Create default admin user
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", password="admin123")
            db.session.add(admin)
            db.session.commit()

    webbrowser.open("http://127.0.0.1:5000")
    socketio.run(app, debug=True)
