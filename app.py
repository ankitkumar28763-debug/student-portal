
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3, os
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "student_portal.db")
UPLOADS = os.path.join(BASE, "uploads")
os.makedirs(UPLOADS, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
ALLOWED = {"pdf", "doc", "docx", "txt", "jpg", "jpeg", "png"}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS students(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      name TEXT NOT NULL,
      course TEXT,
      semester TEXT,
      email TEXT
    );
    CREATE TABLE IF NOT EXISTS admins(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL,
      name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS notices(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      body TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS results(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, subject TEXT, marks INTEGER, grade TEXT
    );
    CREATE TABLE IF NOT EXISTS attendance(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, subject TEXT, percentage INTEGER
    );
    CREATE TABLE IF NOT EXISTS fees(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, semester TEXT, amount INTEGER, status TEXT
    );
    CREATE TABLE IF NOT EXISTS timetable(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      day TEXT, t1 TEXT, t2 TEXT, t3 TEXT, t4 TEXT
    );
    CREATE TABLE IF NOT EXISTS assignments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, subject TEXT, title TEXT, filename TEXT,
      uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS feedback(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, rating INTEGER, message TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS corrections(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      student_id TEXT, field TEXT, current_value TEXT,
      correct_value TEXT, status TEXT DEFAULT 'Pending',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    if not con.execute("SELECT 1 FROM admins WHERE username='admin'").fetchone():
        con.execute("INSERT INTO admins(username,password,name) VALUES(?,?,?)",
                    ("admin","admin123","Portal Administrator"))
    if not con.execute("SELECT 1 FROM students WHERE student_id='STU2026001'").fetchone():
        con.execute("INSERT INTO students(student_id,password,name,course,semester,email) VALUES(?,?,?,?,?,?)",
                    ("STU2026001","12345","Ankit Kumar","BCA","5th Semester","student@example.com"))
        sid = "STU2026001"
        con.executemany("INSERT INTO results(student_id,subject,marks,grade) VALUES(?,?,?,?)", [
            (sid,"Programming",82,"A"),(sid,"Database Management",76,"B+"),
            (sid,"Computer Networks",88,"A+"),(sid,"Software Engineering",79,"A")])
        con.executemany("INSERT INTO attendance(student_id,subject,percentage) VALUES(?,?,?)", [
            (sid,"Programming",82),(sid,"DBMS",76),(sid,"Networks",74)])
        con.executemany("INSERT INTO fees(student_id,semester,amount,status) VALUES(?,?,?,?)", [
            (sid,"Semester 4",20000,"Paid"),(sid,"Semester 5",2500,"Due")])
    if not con.execute("SELECT 1 FROM notices").fetchone():
        con.executemany("INSERT INTO notices(title,body) VALUES(?,?)", [
            ("Semester examination form is open","Complete your examination registration before the deadline."),
            ("Assignment submission deadline updated","Check the Assignment section for submission details."),
            ("Library timing changed","Library timings have been updated.")])
    if not con.execute("SELECT 1 FROM timetable").fetchone():
        con.executemany("INSERT INTO timetable(day,t1,t2,t3,t4) VALUES(?,?,?,?,?)", [
            ("Monday","Programming","DBMS","Break","Networks"),
            ("Tuesday","Networks","Programming","Break","SE"),
            ("Wednesday","DBMS","SE","Break","Programming Lab"),
            ("Thursday","Programming","Networks","Break","DBMS"),
            ("Friday","SE","DBMS","Break","Lab")])
    con.commit(); con.close()

def login_required():
    return "student_id" in session

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        sid = request.form.get("student_id","").strip()
        pw = request.form.get("password","")
        con = db()
        user = con.execute("SELECT * FROM students WHERE student_id=? AND password=?", (sid,pw)).fetchone()
        con.close()
        if user:
            session["student_id"] = sid
            return redirect(url_for("dashboard"))
        flash("Invalid Student ID or Password")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if not login_required(): return redirect(url_for("login"))
    sid=session["student_id"]; con=db()
    user=con.execute("SELECT * FROM students WHERE student_id=?",(sid,)).fetchone()
    att=con.execute("SELECT AVG(percentage) a FROM attendance WHERE student_id=?",(sid,)).fetchone()["a"] or 0
    fees=con.execute("SELECT COALESCE(SUM(amount),0) a FROM fees WHERE student_id=? AND status='Due'",(sid,)).fetchone()["a"]
    assignments=con.execute("SELECT COUNT(*) n FROM assignments WHERE student_id=?",(sid,)).fetchone()["n"]
    notices=con.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 3").fetchall()
    con.close()
    return render_template("dashboard.html", user=user, attendance=round(att), fees=fees, assignments=assignments, notices=notices)

@app.route("/result")
def result():
    if not login_required(): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM results WHERE student_id=?",(session["student_id"],)).fetchall(); con.close()
    return render_template("page.html", title="Result Check", content="result", rows=rows)

@app.route("/attendance")
def attendance():
    if not login_required(): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM attendance WHERE student_id=?",(session["student_id"],)).fetchall(); con.close()
    return render_template("page.html", title="Attendance Check", content="attendance", rows=rows)

@app.route("/fees")
def fees():
    if not login_required(): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM fees WHERE student_id=?",(session["student_id"],)).fetchall(); con.close()
    return render_template("page.html", title="Fees", content="fees", rows=rows)

@app.route("/notice")
def notice():
    if not login_required(): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM notices ORDER BY id DESC").fetchall(); con.close()
    return render_template("page.html", title="Notice", content="notice", rows=rows)

@app.route("/timetable")
def timetable():
    if not login_required(): return redirect(url_for("login"))
    con=db(); rows=con.execute("SELECT * FROM timetable").fetchall(); con.close()
    return render_template("page.html", title="Time Table", content="timetable", rows=rows)

@app.route("/assignment", methods=["GET","POST"])
def assignment():
    if not login_required(): return redirect(url_for("login"))
    if request.method=="POST":
        subject=request.form.get("subject","").strip()
        title=request.form.get("title","").strip()
        file=request.files.get("file")
        if not subject or not title or not file or not file.filename:
            flash("Subject, title and file are required.")
            return redirect(url_for("assignment"))
        ext=file.filename.rsplit(".",1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED:
            flash("File type not allowed.")
            return redirect(url_for("assignment"))
        filename=secure_filename(f"{session['student_id']}_{file.filename}")
        file.save(os.path.join(UPLOADS,filename))
        con=db(); con.execute("INSERT INTO assignments(student_id,subject,title,filename) VALUES(?,?,?,?)",
                              (session["student_id"],subject,title,filename)); con.commit(); con.close()
        flash("Assignment uploaded successfully.")
        return redirect(url_for("assignment"))
    con=db(); rows=con.execute("SELECT * FROM assignments WHERE student_id=? ORDER BY id DESC",(session["student_id"],)).fetchall(); con.close()
    return render_template("assignment.html", rows=rows)

@app.route("/download/<path:filename>")
def download(filename):
    if not login_required(): return redirect(url_for("login"))
    return send_from_directory(UPLOADS, filename, as_attachment=True)

@app.route("/profile")
def profile():
    if not login_required(): return redirect(url_for("login"))
    con=db(); user=con.execute("SELECT * FROM students WHERE student_id=?",(session["student_id"],)).fetchone(); con.close()
    return render_template("page.html", title="Profile", content="profile", user=user)

@app.route("/feedback", methods=["GET","POST"])
def feedback():
    if not login_required(): return redirect(url_for("login"))
    if request.method=="POST":
        con=db(); con.execute("INSERT INTO feedback(student_id,rating,message) VALUES(?,?,?)",
                              (session["student_id"],request.form["rating"],request.form["message"]))
        con.commit(); con.close(); flash("Feedback submitted successfully."); return redirect(url_for("feedback"))
    return render_template("feedback.html")

@app.route("/correction", methods=["GET","POST"])
def correction():
    if not login_required(): return redirect(url_for("login"))
    if request.method=="POST":
        con=db(); con.execute("INSERT INTO corrections(student_id,field,current_value,correct_value) VALUES(?,?,?,?)",
                              (session["student_id"],request.form["field"],request.form["current_value"],request.form["correct_value"]))
        con.commit(); con.close(); flash("Correction request submitted."); return redirect(url_for("correction"))
    return render_template("correction.html")


def admin_required():
    return "admin" in session

@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        con=db()
        a=con.execute("SELECT * FROM admins WHERE username=? AND password=?",(username,password)).fetchone()
        con.close()
        if a:
            session["admin"]=username
            session["admin_name"]=a["name"]
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin username or password.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin",None); session.pop("admin_name",None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    counts={
      "students":con.execute("SELECT COUNT(*) n FROM students").fetchone()["n"],
      "notices":con.execute("SELECT COUNT(*) n FROM notices").fetchone()["n"],
      "assignments":con.execute("SELECT COUNT(*) n FROM assignments").fetchone()["n"],
      "feedback":con.execute("SELECT COUNT(*) n FROM feedback").fetchone()["n"],
      "corrections":con.execute("SELECT COUNT(*) n FROM corrections WHERE status='Pending'").fetchone()["n"]
    }
    students=con.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    con.close()
    return render_template("admin_dashboard.html",counts=counts,students=students)

@app.route("/admin/student/add", methods=["POST"])
def admin_student_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    try:
        con=db()
        con.execute("""INSERT INTO students(student_id,password,name,course,semester,email)
                       VALUES(?,?,?,?,?,?)""",
                    (request.form["student_id"],request.form["password"],request.form["name"],
                     request.form.get("course",""),request.form.get("semester",""),request.form.get("email","")))
        con.commit(); con.close()
        flash("Student added successfully.")
    except sqlite3.IntegrityError:
        flash("Student ID already exists.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/student/delete/<int:student_pk>", methods=["POST"])
def admin_student_delete(student_pk):
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    st=con.execute("SELECT student_id FROM students WHERE id=?",(student_pk,)).fetchone()
    if st:
        sid=st["student_id"]
        for table in ("results","attendance","fees","assignments","feedback","corrections"):
            con.execute(f"DELETE FROM {table} WHERE student_id=?",(sid,))
        con.execute("DELETE FROM students WHERE id=?",(student_pk,))
        con.commit()
        flash("Student and related demo records deleted.")
    con.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/result/add", methods=["POST"])
def admin_result_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    marks=int(request.form["marks"])
    grade = "A+" if marks>=85 else "A" if marks>=75 else "B+" if marks>=65 else "B" if marks>=55 else "C"
    con=db()
    con.execute("INSERT INTO results(student_id,subject,marks,grade) VALUES(?,?,?,?)",
                (request.form["student_id"],request.form["subject"],marks,grade))
    con.commit(); con.close(); flash("Result added.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/attendance/add", methods=["POST"])
def admin_attendance_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    con.execute("INSERT INTO attendance(student_id,subject,percentage) VALUES(?,?,?)",
                (request.form["student_id"],request.form["subject"],int(request.form["percentage"])))
    con.commit(); con.close(); flash("Attendance updated.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/fee/add", methods=["POST"])
def admin_fee_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    con.execute("INSERT INTO fees(student_id,semester,amount,status) VALUES(?,?,?,?)",
                (request.form["student_id"],request.form["semester"],int(request.form["amount"]),request.form["status"]))
    con.commit(); con.close(); flash("Fee record added.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/notice/add", methods=["POST"])
def admin_notice_add():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    con.execute("INSERT INTO notices(title,body) VALUES(?,?)",(request.form["title"],request.form["body"]))
    con.commit(); con.close(); flash("Notice published.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/correction")
def admin_corrections():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    rows=con.execute("""SELECT c.*,s.name FROM corrections c
                       LEFT JOIN students s ON s.student_id=c.student_id
                       ORDER BY c.id DESC""").fetchall()
    con.close()
    return render_template("admin_corrections.html",rows=rows)

@app.route("/admin/correction/<int:cid>/<status>", methods=["POST"])
def admin_correction_status(cid,status):
    if not admin_required(): return redirect(url_for("admin_login"))
    if status not in ("Approved","Rejected","Pending"): status="Pending"
    con=db(); con.execute("UPDATE corrections SET status=? WHERE id=?",(status,cid)); con.commit(); con.close()
    flash("Correction status updated.")
    return redirect(url_for("admin_corrections"))

@app.route("/admin/feedback")
def admin_feedback():
    if not admin_required(): return redirect(url_for("admin_login"))
    con=db()
    rows=con.execute("""SELECT f.*,s.name FROM feedback f
                       LEFT JOIN students s ON s.student_id=f.student_id
                       ORDER BY f.id DESC""").fetchall()
    con.close()
    return render_template("admin_feedback.html",rows=rows)

@app.route("/simple/<name>")
def simple(name):
    if not login_required(): return redirect(url_for("login"))
    titles={"notes":"Check Notes","exam":"Exam Registration","datesheet":"Date Sheet","antiragging":"Anti-Ragging"}
    return render_template("simple.html", title=titles.get(name,name.title()), name=name)

init_db()
if __name__ == "__main__":
    app.run(debug=True)
