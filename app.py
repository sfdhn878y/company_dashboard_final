from flask import Flask,render_template,request,session,redirect,url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import or_

app = Flask(__name__)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///placement.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "mysecret123"
db = SQLAlchemy(app)

# =====================
# MODELS
# =====================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    role = db.Column(db.String(20), nullable=False)  # admin / student / company
    is_approved = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ ONE TO ONE RELATIONSHIPS
    student_profile = db.relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete"
    )

    company_profile = db.relationship(
        "CompanyProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete"
    )

class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ UNIQUE ensures one profile per user
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    department = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    resume = db.Column(db.String(200))

    user = db.relationship("User", back_populates="student_profile")

    applications = db.relationship(
        "Application",
        back_populates="student",
        cascade="all, delete"
    )

        
class CompanyProfile(db.Model):
    __tablename__ = "company_profiles"

    id = db.Column(db.Integer, primary_key=True)

    # ✅ UNIQUE prevents duplicates
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        unique=True
    )

    company_name = db.Column(db.String(150))
    industry = db.Column(db.String(100))
    website = db.Column(db.String(150))

    description = db.Column(db.Text)
    location = db.Column(db.String(100))
    company_size = db.Column(db.String(50))

    user = db.relationship("User", back_populates="company_profile")

    jobs = db.relationship(
        "Job",
        back_populates="company",
        cascade="all, delete"
    )

class Job(db.Model):
    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)

    company_id = db.Column(
        db.Integer,
        db.ForeignKey("company_profiles.id"),
        nullable=False
    )

    title = db.Column(db.String(150))
    skills = db.Column(db.String(200))
    salary = db.Column(db.String(50))

    is_approved = db.Column(db.Boolean, default=False)
    is_closed = db.Column(db.Boolean, default=False)

    company = db.relationship("CompanyProfile", back_populates="jobs")

    applications = db.relationship(
        "Application",
        back_populates="job",
        cascade="all, delete"
    )

class Application(db.Model):
    __tablename__ = "applications"

    id = db.Column(db.Integer, primary_key=True)

    job_id = db.Column(
        db.Integer,
        db.ForeignKey("jobs.id"),
        nullable=False
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student_profiles.id"),
        nullable=False
    )

    status = db.Column(db.String(50), default="Applied")
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    job = db.relationship("Job", back_populates="applications")
    student = db.relationship("StudentProfile", back_populates="applications")







@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]  # student / company

        # block admin registration
        if role == "admin":
            return "Admin cannot be registered"

        if User.query.filter_by(email=email).first():
            return "Email already registered"

        user = User(
            name=name,
            email=email,
            password=password,
            role=role,
            is_approved=False if role == "company" else True
        )

        db.session.add(user)
        db.session.commit()
    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user:
            print('186 line ')
            return "No user found"

        
        if not (user.password, password):
            print(user.password,password)
            return "Wrong password" 
        session["user_id"] = user.id
        session["role"] = user.role
        if user.role == "company" and not user.is_approved:
            return "u are not approved"

    

        if user.role == "Admin":
            return redirect('admin_dashboard')

        elif user.role == "company":
            return redirect('company_dashboard')

        else:
            return redirect('student_dashboard')

    return render_template("login.html")












@app.route("/company_dashboard")
def company_dashboard():
    if "user_id" not in session:
        return redirect("/login")

    company = CompanyProfile.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not company:
        return redirect("/complete-company-profile")

    jobs = Job.query.filter_by(company_id=company.id).all()

    job_data = []
    all_shortlisted = []   # ⭐ NEW LIST

    for job in jobs:
        total_apps = Application.query.filter_by(job_id=job.id).count()

        shortlisted = Application.query.filter_by(
            job_id=job.id,
            status="Shortlisted"
        ).all()

        all_shortlisted.extend(shortlisted)  # ⭐ collect all

        job_data.append({
            "job": job,
            "total_apps": total_apps
        })

    return render_template(
        "company_dashboard.html",
        company=company,
        jobs=job_data,
        shortlisted=all_shortlisted   # ⭐ PASS GLOBAL LIST
    )















    
@app.route("/toggle-job/<int:id>")
def toggle_job(id):
    job = Job.query.get_or_404(id)

    job.is_closed = not job.is_closed   # ✅ toggles True ↔ False

    db.session.commit()
    return redirect("/company_dashboard")



@app.route("/toggle-status/<int:app_id>/<string:action>")
def toggle_status(app_id, action):
    if "user_id" not in session:
        return redirect("/login")

    application = Application.query.get_or_404(app_id)

    if action == "shortlist":
        if application.status == "Shortlisted":
            application.status = "Applied"   # unshortlist
        else:
            application.status = "Shortlisted"

    elif action == "select":
        if application.status == "Selected":
            application.status = "Shortlisted"   # unselect
        else:
            application.status = "Selected"

    elif action == "reject":
        if application.status == "Rejected":
            application.status = "Applied"   # unreject
        else:
            application.status = "Rejected"

    db.session.commit()

    return redirect(request.referrer)



@app.route("/job-applications/<int:job_id>")
def view_applications(job_id):
    applications = Application.query.filter_by(job_id=job_id).all()

    return render_template(
        "applications.html",
        applications=applications
    )



@app.route("/update-status/<int:app_id>/<status>")
def update_status(app_id, status):
    application = Application.query.get_or_404(app_id)

    application.status = status

    db.session.commit()

    return redirect(request.referrer)

    
@app.route("/post-job", methods=["GET", "POST"])
def post_job():
    if "user_id" not in session:
        return redirect("/login")

    company = CompanyProfile.query.filter_by(user_id=session["user_id"]).first()

    if not company:
        return "Please complete company profile first"

    if request.method == "POST":
        job = Job(
            company_id=company.id,
            title=request.form["title"],
            skills=request.form["skills"],
            salary=request.form["salary"],

        )

        db.session.add(job)
        db.session.commit()

        return redirect("/company_dashboard")

    return render_template("post_job.html")

@app.route("/delete-job/<int:id>")
def delete_job(id):
    job = Job.query.get_or_404(id)

    db.session.delete(job)
    db.session.commit()

    return redirect("/company_dashboard")

@app.route("/edit-job/<int:id>", methods=["GET", "POST"])
def edit_job(id):
    job = Job.query.get_or_404(id)

    if request.method == "POST":
        job.title = request.form["title"]
        job.skills = request.form["skills"]
        job.experience = request.form["experience"]
        job.salary = request.form["salary"]
        job.description = request.form["description"]

        db.session.commit()
        return redirect("/company_dashboard")

    return render_template("edit_job.html", job=job)


@app.route("/complete-company-profile", methods=["GET", "POST"])
def complete_company_profile():

    user_id = session.get("user_id")  #2

    if not user_id:
        return redirect("/login")

    company = CompanyProfile.query.filter_by(user_id=user_id).first()

    if request.method == "POST":

        # ✅ CASE 1: Profile exists → UPDATE
        if company:
            company.company_name = request.form["company_name"]
            company.industry = request.form["industry"]
            company.website = request.form["website"]
            company.location = request.form["location"]
            company.company_size = request.form["company_size"]
            company.description = request.form["description"]

        # ✅ CASE 2: First time → INSERT
        else:
            company = CompanyProfile(
                user_id=user_id,
                company_name=request.form["company_name"],
                industry=request.form["industry"],
                website=request.form["website"],
                location=request.form["location"],
                company_size=request.form["company_size"],
                description=request.form["description"]
            )   
            db.session.add(company)

        db.session.commit()
        return redirect("/company_dashboard")

    return render_template("complete_company_profile.html", company=company)


from sqlalchemy import or_
from sqlalchemy.orm import joinedload

@app.route("/admin_dashboard")
def admin_dashboard():

    student_search = request.args.get("student_search", "")
    company_search = request.args.get("company_search", "")

    # Companies
    companies = User.query.options(
        joinedload(User.company_profile)
    ).filter_by(role="company", is_approved=True)

    if company_search:
        companies = companies.filter(
            User.company_profile.has(
                or_(
                    CompanyProfile.company_name.ilike(f"%{company_search}%"),
                    CompanyProfile.industry.ilike(f"%{company_search}%")
                )
            )
        )

    companies = companies.all()

    # Students
    students = User.query.filter_by(role="student", is_approved=True)

    if student_search:
        students = students.filter(
            or_(
                User.name.ilike(f"%{student_search}%"),
                User.email.ilike(f"%{student_search}%")
            )
        )

    students = students.all()

    # Pending Companies
    pending_companies = User.query.options(
        joinedload(User.company_profile)
    ).filter_by(role="company", is_approved=False).all()

    # Jobs
    jobs = Job.query.all()

    ongoing_jobs = Job.query.filter_by(
        is_approved=True,
        is_closed=False
    ).all()

    # Applications
    applications = Application.query.options(
        joinedload(Application.student).joinedload(StudentProfile.user),
        joinedload(Application.job)
    ).all()

    return render_template(
        "admin_dashboard.html",
        companies=companies,
        students=students,
        pending_companies=pending_companies,
        jobs=jobs,
        ongoing_jobs=ongoing_jobs,
        applications=applications
    )
# approve job
@app.route("/approve-job/<int:id>")
def approve_job(id):
    job = Job.query.get(id)
    if job:
        job.is_approved = True
        db.session.commit()
    return redirect("/admin_dashboard")

# reject job (you can delete or just mark rejected)
@app.route("/disapprove-job/<int:id>")
def disapprove_job(id):
    job = Job.query.get(id)

    if job:

        # check if any application exists for this job
        application_count = Application.query.filter_by(job_id=id).count()

        # if students already applied → do NOT allow disapprove
        if application_count > 0:
            return "Cannot disapprove. Students already applied to this job."

        # if no applications → allow disapprove
        job.is_approved = False
        db.session.commit()

    return redirect("/admin_dashboard")





@app.route("/admin-job/<int:job_id>")
def admin_job_details(job_id):

    job = Job.query.get_or_404(job_id)

    # get company info
    company = job.company   # make sure relationship exists

    # get all applications for this job
    applications = Application.query.filter_by(job_id=job_id).all()

    return render_template(
        "admin_job_details.html",
        job=job,
        company=company,
        applications=applications
    )

#-----------------------------------------------------------------

@app.route("/student_dashboard")
def student_dashboard():

    # 🔒 Check login
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    student = StudentProfile.query.filter_by(user_id=user_id).first()

    # Get approved + open jobs
    jobs = Job.query.filter_by(is_approved=True, is_closed=False).all()

    # Get student applications
    applications = Application.query.filter_by(student_id=student.id).all()

    # Create mapping {job_id : status}
    application_status = {app.job_id: app.status for app in applications}

    return render_template(
        "student_dashboard.html",
        student=student,
        jobs=jobs,
        application_status=application_status
    )

@app.route("/apply-job/<int:job_id>")
def apply_job(job_id):
    if "user_id" not in session:
        return redirect("/login")

    student = StudentProfile.query.filter_by(
        user_id=session["user_id"]).first()

    if not student:
        return "Complete profile first!"

    # Check duplicate apply
    existing = Application.query.filter_by(
        job_id=job_id,
        student_id=student.id
    ).first()

    if existing:
        return "Already applied!"

    app = Application(
        job_id=job_id,
        student_id=student.id
    )

    db.session.add(app)
    db.session.commit()

    return redirect("/student_dashboard")


@app.route("/complete-student-profile", methods=["GET", "POST"])
def complete_student_profile():
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    student = StudentProfile.query.filter_by(user_id=user_id).first()

    if request.method == "POST":

        if not student:
            student = StudentProfile(user_id=user_id)
            db.session.add(student)

        student.department = request.form["department"]
        student.cgpa = request.form["cgpa"]
        student.resume = request.form["resume"]

        db.session.commit()

        return redirect("/student_dashboard")

    return render_template("complete_student_profile.html", student=student)


@app.route("/schedule-interview/<int:id>", methods=["GET","POST"])
def schedule_interview(id):
    app_obj = Application.query.get_or_404(id)

    if request.method == "POST":
        date = request.form["date"]
        app_obj.interview_date = date
        db.session.commit()
        return redirect("/company-dashboard")

    return render_template("schedule.html", app=app_obj)

@app.route("/toggle-shortlist/<int:id>")
def toggle_shortlist(id):
    app_obj = Application.query.get_or_404(id)

    app_obj.is_shortlisted = not app_obj.is_shortlisted
    db.session.commit()

    return redirect(request.referrer)

#--------------------------------------------

@app.route("/admin-company/<int:user_id>")
def admin_company_details(user_id):

    # Get company user
    company_user = User.query.filter_by(
        id=user_id,
        role="company"
    ).first_or_404()

    company_profile = company_user.company_profile

    # Get all jobs posted by company
    jobs = Job.query.filter_by(
        company_id=company_profile.id
    ).all()

    # Get applications for all jobs
    applications = Application.query.join(Job).filter(
        Job.company_id == company_profile.id
    ).all()

    return render_template(
        "admin_company_details.html",
        company_user=company_user,
        company_profile=company_profile,
        jobs=jobs,
        applications=applications
    )














@app.route('/logout')
def logout():
    session.clear()  # clears the session for the user
    return redirect(url_for('login'))  # redirect to login page









# =====================
# RUN
# =====================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        existing_admin = User.query.filter_by(name="admin").first()

        if not existing_admin:

            admin_db = User(
                name = 'admin',
                password ='admin',
                email = 'admin@gmail.com',
                role='Admin'
            )
            db.session.add(admin_db)
            db.session.commit()
    app.run(debug=True)