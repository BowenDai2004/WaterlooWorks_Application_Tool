# app.py
import pprint
from sqlite3 import IntegrityError
from flask import Flask, redirect, send_file, url_for, render_template, request, flash, jsonify, send_file

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from flask_login import LoginManager, login_required, UserMixin, login_user, current_user, logout_user

from flask_bcrypt import Bcrypt

import os
import re
import io
import zipfile

from scraper import *
from coverLetter import *

Employer_Student_Direct_Job_Board_url = "https://waterlooworks.uwaterloo.ca/myAccount/co-op/direct/jobs.htm"
Full_Cycle_Service_Job_Board_url = "https://waterlooworks.uwaterloo.ca/myAccount/co-op/full/jobs.htm"


app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+ db_path
# TODO store the secret key as an encironmnent variable, to change before deployment
app.config['SECRET_KEY'] = "28652846f179f15321b529fd9abd7595"
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# TODO manage driver more properly
driverDict = {}

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String(200), nullable = False, unique = True)
    password = db.Column(db.String(200), nullable = False)
    resume = db.Column(db.Text, nullable = True)    
    userInfo = db.Column(JSON)

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

class CoverLetter(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    fileName = db.Column(db.String(200), nullable = False)
    userId = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable = False)
    jobId = db.Column(db.Integer, db.ForeignKey("job.id", ondelete = "CASCADE"), nullable = False)
    
    pdf = db.Column(db.LargeBinary, nullable=False)
    latex = db.Column(db.Text, nullable = False) 
    
    coverLetter = db.Column(JSON, nullable = False)
    toApply = db.Column(db.Boolean, default= True)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    jobDict = db.Column(JSON)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def home():
    return render_template("home.html")

@app.route("/register", methods = ["POST", "GET"])
def register():
    if request.method == "POST":
        email = request.form["Email"]
        password = request.form["Password"]
        if User.query.filter_by(email = email).first():
            flash("This email is already registed", "danger")
            return redirect(url_for('register'))
        else:
            new_user = User(email=email)
            new_user.set_password(password=password)
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form["Email"]
        password = request.form["Password"]
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            if current_user.resume != "":
                return redirect(url_for("home"))
            else:
                return redirect(url_for("inputResume"))
        else:
            flash("Invalide email or password","danger")
    return render_template("login.html")

@app.route("/inputResume", methods = ["POST","GET"])
@login_required
def inputResume():
    if request.method == "POST":
        current_user.resume = request.form["Resume"]
        current_user.userInfo = extractUserInfo(current_user.resume)
        db.session.commit()
        return redirect(url_for("confirmUserInfo"))
    return render_template("inputResume.html", resume = current_user.resume)

# TODO update the existing letter if user info is changed
@app.route("/confirmUserInfo", methods = ["POST","GET"])
@login_required
def confirmUserInfo():
    if request.method == "POST":
        current_user.userInfo = request.form.to_dict()
        currentCoverLetters = CoverLetter.query.filter(CoverLetter.userId == current_user.id).all()
        for letter in currentCoverLetters:
            letter.latex = fillTemplate(jobDetail=Job.query.get(letter.jobId).jobDict, userInfo=current_user.userInfo, coverLetter=letter.coverLetter, templatePath="templates")
            letter.pdf = latexToPDF(letter.latex)
        db.session.commit()
        return redirect(url_for("waterlooworkInfo"))
    
    return render_template("confirmUserInfo.html", data=current_user.userInfo)

@app.route("/waterlooworkInfo", methods = ["POST","GET"])
@login_required
def waterlooworkInfo():
    return render_template("waterlooworkInfo.html")

@app.route("/waterlooworkLogin", methods = ["POST", "GET"])
@login_required
def waterlooworkLogin():
    driver = createChromeDriver()
    driverDict[current_user.id] = driver
    data = request.get_json()
    return getVerificationCode(username=data["WaterlooEmail"], password=data["Password"], driver=driver)

#TODO dublicated cover letters
#TODO delete old cover letters
@app.route("/generatePDFCoverLetter", methods = ["POST"])
@login_required
def generatePDFCoverLetter():
    session = createSession()
    setCookies(getCookie(driver=driverDict[current_user.id]),session)
    rawToken = getRawTokenHtml(session=session, coopUrl = Full_Cycle_Service_Job_Board_url)
    jobIDList = getJobIDList(rawTokenHtml=rawToken, session=session, coopUrl=Full_Cycle_Service_Job_Board_url, folderValue=[getFolderOption(rawTokenHtml=rawToken, folderName=request.get_json()["JobFolderName"])])

    jobList = []
    coverLetterList = []
    for id in jobIDList:
        job = Job.query.filter_by(id=id).first()
        if not job:
            job = Job(id = id, jobDict = extractJobDetail(getJobDetail(id,getJobDetailToken(rawToken),session, coopUrl=Full_Cycle_Service_Job_Board_url), id))
            db.session.add(job)
        jobList.append(job.jobDict)
        coverLetterList.append(generateCoverLetter(job.jobDict, current_user.resume))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    
    for i in range(len(jobIDList)):
        texCoverLetter = fillTemplate(jobDetail=jobList[i], coverLetter=coverLetterList[i], userInfo=current_user.userInfo, templatePath="templates")
        pdfCoverLetter = latexToPDF(texCoverLetter)
        newCoverLetter = CoverLetter(fileName = f"{sanitize_filename(Job.query.get(jobIDList[i]).jobDict['Job Title'])}_{sanitize_filename(Job.query.get(jobIDList[i]).jobDict['Company'])}.pdf", pdf = pdfCoverLetter, latex=texCoverLetter, userId = current_user.id, jobId=int(jobIDList[i]), coverLetter=coverLetterList[i])
        db.session.add(newCoverLetter)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/coverLetterList")
@login_required
def coverLetterList():
    coverLetterList = CoverLetter.query.filter(
        CoverLetter.userId == current_user.id,
        CoverLetter.toApply == True
    ).all()
    
    return render_template("coverLetterList.html", coverLetterList=coverLetterList )

@app.route("/viewCoverLetter/<coverLetter_id>", methods = ["POST", "GET"])
@login_required
def viewCoverLetter(coverLetter_id):
    if request.method == "POST":
        newTitle = request.form["Title"]
        paragraphs = re.split(r"\n+",request.form["Paragraphs"])
        newParagraphs = [paragraph.strip() for paragraph in paragraphs if paragraph.strip()]
        currentCoverLetter = CoverLetter.query.get(coverLetter_id)
        currentCoverLetter.coverLetter = {
            "Title": newTitle,
            "Paragraphs": newParagraphs
        }
        currentCoverLetter.latex = fillTemplate(jobDetail=Job.query.get(currentCoverLetter.jobId).jobDict, userInfo=current_user.userInfo, coverLetter=currentCoverLetter.coverLetter, templatePath="templates")
        currentCoverLetter.pdf = latexToPDF(currentCoverLetter.latex)
        db.session.commit()
        
    coverLetter = CoverLetter.query.get(coverLetter_id)
    prev = CoverLetter.query.filter(CoverLetter.id < coverLetter_id).order_by(CoverLetter.id.desc()).first()
    next = CoverLetter.query.filter(CoverLetter.id > coverLetter_id).order_by(CoverLetter.id.asc()).first()
    return render_template("viewCoverLetter.html",
                           job = Job.query.get(coverLetter.jobId),
                           coverLetter= coverLetter,
                           prev_id = prev.id if prev else None,
                           next_id = next.id if next else None)

@app.route("/coverLetterPdf/<coverLetter_id>")
@login_required
def coverLetterPdf(coverLetter_id):
    coverLetter = CoverLetter.query.get(coverLetter_id)
    return send_file(
        io.BytesIO(coverLetter.pdf),
        mimetype = "application/pdf",
        download_name= coverLetter.fileName)

@app.route("/improveCoverLetter/<coverLetter_id>", methods = ["POST"])
@login_required
def improveCoverLetter(coverLetter_id):
    userFeedback = request.form["userFeedback"]
    coverLetter = CoverLetter.query.get(coverLetter_id)
    improvedCoverLetter = generateImproveCoverLetter(coverLetter.coverLetter, userFeedback)
    coverLetter.coverLetter = improvedCoverLetter
    coverLetter.latex = fillTemplate(jobDetail=Job.query.get(coverLetter.jobId).jobDict, userInfo=current_user.userInfo, coverLetter=coverLetter.coverLetter, templatePath="templates")
    coverLetter.pdf = latexToPDF(coverLetter.latex)
    db.session.commit()
    return redirect(url_for("viewCoverLetter", coverLetter_id=coverLetter.id))

@app.route("/downloadCoverLetter/<coverLetter_id>")
@login_required
def downloadCoverLetter(coverLetter_id):
    coverLetter = CoverLetter.query.get(coverLetter_id)
    return send_file(
        io.BytesIO(coverLetter.pdf),
        mimetype = "application/pdf",
        as_attachment=True,
        download_name= f"{coverLetter.fileName}.pdf"
    )

@app.route("/downloadAllCoverLetter")
@login_required
def downloadAllCoverLetter():
    coverLetterList = CoverLetter.query.filter(
        CoverLetter.userId == current_user.id,
    ).all()
    zipBuffer = io.BytesIO()
    with zipfile.ZipFile(zipBuffer, "w") as zipFile:
        for coverLetter in coverLetterList:
            zipFile.writestr(f"{coverLetter.fileName}.pdf", coverLetter.pdf)
    zipBuffer.seek(0)
    return send_file(
        zipBuffer,
        mimetype = "application/zip",
        download_name= "CoverLetters.zip"
    )

@app.route("/apply")
@login_required
def apply():
    return jsonify({"status" : "ok"})

@app.route("/logout")
@login_required
def logout():
    if current_user.id in driverDict:
        driverDict[current_user.id].close()
        driverDict.pop(current_user.id)
    logout_user()
    return redirect(url_for("login"))

if __name__ == "__main__":
    with app.app_context():
        #db.drop_all()
        db.create_all()
        pprint.pprint(db.Model.metadata.tables.keys())
    app.run(debug=True, host="0.0.0.0", port=5000)