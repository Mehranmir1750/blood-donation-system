from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import login_user, LoginManager, UserMixin, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecret123")
app.config['WTF_CSRF_ENABLED'] = True

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'home'

# ── DATABASE ──
class Base(DeclarativeBase):
    pass

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    "DATABASE_URL",
    "sqlite:///bloodDonation.db"
)

db = SQLAlchemy(model_class=Base)
db.init_app(app)

# ── MODELS ──
class Users(db.Model, UserMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(300), nullable=False)
    contact: Mapped[str] = mapped_column(String(15), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50))
    status = db.Column(db.String(20), default='Pending')

class Blood_stock(db.Model):
    __tablename__ = "blood_stock"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    hospital_name: Mapped[str] = mapped_column(String(1000), nullable=False)
    hospital_contact: Mapped[str] = mapped_column(String(100), nullable=False)
    blood_group: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    units_available: Mapped[int] = mapped_column(Integer, nullable=False)

class Donors(db.Model):
    __tablename__ = "donors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email: Mapped[str] = mapped_column(String(500), nullable=False)
    contact: Mapped[str] = mapped_column(String(15), nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    blood_group: Mapped[str] = mapped_column(String(80), nullable=False)
    address: Mapped[str] = mapped_column(String(1000), nullable=False)

class Requests(db.Model):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    email = db.Column(db.String(120))
    blood_group: Mapped[str] = mapped_column(String(80), nullable=False)
    units_requested: Mapped[int] = mapped_column(Integer, nullable=False)
    contact: Mapped[str] = mapped_column(String(15), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=False)
    status = db.Column(db.String(20), default='Pending')

# ── FORMS ──
class RegisterForm(FlaskForm):
    username = StringField("Full Name / Hospital Name", validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    contact = StringField("Contact Number", validators=[DataRequired(), Length(min=10, max=15)])
    address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    role = SelectField("Register As", choices=[('hospital', 'Hospital'), ('patient', 'Patient')], validators=[DataRequired()])
    submit = SubmitField("Create Account")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Users, int(user_id))

with app.app_context():
    db.create_all()

# ── ROUTES ──

@app.route("/")
def home():
    return render_template("home.html")

@app.route('/register', methods=['GET', 'POST'])
def Registration_page():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = Users.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered!", category='danger')
            return redirect(url_for('Registration_page'))

        new_user = Users(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data),
            contact=form.contact.data,
            address=form.address.data,
            role=form.role.data
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully!", category='success')

        if form.role.data == 'hospital':
            return redirect(url_for('hospital_confirm'))
        elif form.role.data == 'patient':
            new_user.status = 'Approved'
            db.session.commit()
            return redirect(url_for('patient_login'))
        else:
            return redirect(url_for('admin_login'))

    return render_template('Registration_page.html', form=form)

@app.route("/hospital_login", methods=["GET", "POST"])
def hospital_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(
            email=form.email.data,
            role="hospital",
            status="Approved"
        ).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("view_hospital"))
        else:
            flash("Invalid credentials or account not approved yet.", "danger")
    return render_template("hospital_login.html", form=form)

@app.route('/patient_login', methods=["GET", "POST"])
def patient_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data, role="patient").first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('patient_dashboard'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("patient_login.html", form=form)

@app.route('/admin_login', methods=['POST', 'GET'])
def admin_login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data, role="admin").first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("admin_login.html", form=form)

@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    requests = Requests.query.filter_by(patient_id=current_user.id).all()
    return render_template('patient_dashboard.html', requests=requests)

@app.route('/view_hospital')
@login_required
def view_hospital():
    stocks = Blood_stock.query.filter_by(hospital_id=current_user.id).all()
    return render_template('view_hospital.html', blood_stocks=stocks)

@app.route('/donors')
@login_required
def donors():
    donors = Donors.query.all()
    return render_template('donors.html', donors=donors)

@app.route('/blood_requests', methods=['GET'])
@login_required
def blood_requests():
    requests = Requests.query.all()
    return render_template('blood_requests.html', requests=requests)

@app.route('/add_blood_stock', methods=['GET', 'POST'])
@login_required
def add_blood_stock():
    if request.method == 'POST':
        blood_group = request.form['blood_group']
        units_available = int(request.form['units_available'])
        hospital_name = request.form['hospital_name']
        hospital_contact = request.form['hospital_contact']
        address = request.form['address']

        existing = Blood_stock.query.filter_by(
            hospital_id=current_user.id,
            blood_group=blood_group
        ).first()

        if existing:
            existing.units_available += units_available
        else:
            new_stock = Blood_stock(
                hospital_id=current_user.id,
                hospital_name=hospital_name,
                hospital_contact=hospital_contact,
                blood_group=blood_group,
                address=address,
                units_available=units_available
            )
            db.session.add(new_stock)
            flash(f"🩸 Added new blood group {blood_group}!", "success")

        db.session.commit()
        flash('✅ Blood stock added successfully!', 'success')
        return redirect(url_for('view_hospital'))

    return render_template('add_blood_stock.html')

@app.route('/update_blood_stock/<int:stock_id>', methods=['GET', 'POST'])
@login_required
def update_blood_stock(stock_id):
    stock = Blood_stock.query.get_or_404(stock_id)
    if request.method == 'POST':
        stock.blood_group = request.form['blood_group']
        stock.units_available = request.form['units_available']
        db.session.commit()
        flash('✅ Blood stock updated successfully!', 'success')
        return redirect(url_for('view_hospital'))
    return render_template('update_blood_stock.html', stock=stock)

@app.route('/delete_blood_stock/<int:stock_id>', methods=['GET'])
@login_required
def delete_blood_stock(stock_id):
    stock = Blood_stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    flash('🗑️ Blood stock deleted successfully!', 'success')
    return redirect(url_for('view_hospital'))

@app.route('/check_availability', methods=['GET'])
@login_required
def check_availability():
    blood_stock = Blood_stock.query.all()
    return render_template('check_availability.html', blood_stock=blood_stock)

@app.route('/p_blood_request', methods=['POST', 'GET'])
@login_required
def p_blood_request():
    if request.method == "POST":
        new_request = Requests(
            patient_id=current_user.id,
            name=request.form['name'],
            blood_group=request.form['blood_group'],
            units_requested=request.form['units_requested'],
            contact=request.form['contact'],
            address=request.form['address']
        )
        db.session.add(new_request)
        db.session.commit()
        flash('✅ Blood request submitted successfully!', 'success')
        return redirect(url_for('patient_dashboard'))
    return render_template('p_blood_request.html')

@app.route('/become_donor', methods=['POST', 'GET'])
@login_required
def become_donor():
    if request.method == "POST":
        donor = Donors(
            hospital_id=current_user.id,
            name=request.form['name'],
            email=request.form['email'],
            contact=request.form['contact'],
            age=request.form['age'],
            blood_group=request.form['blood_group'],
            address=request.form['address']
        )
        db.session.add(donor)
        db.session.commit()
        flash('✅ Donor registered successfully!', 'success')
        return redirect(url_for('become_donor'))
    return render_template('become_donor.html')

@app.route('/approve_request/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    req = Requests.query.get_or_404(request_id)
    req.status = 'Approved'
    db.session.commit()
    flash("✅ Request approved successfully!", "success")
    return redirect(url_for('blood_requests'))

@app.route('/reject_request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    req = Requests.query.get_or_404(request_id)
    req.status = 'Rejected'
    db.session.commit()
    flash("❌ Request rejected.", "info")
    return redirect(url_for('blood_requests'))

@app.route('/admin_dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash("❌ Access denied!", "danger")
        return redirect(url_for('home'))
    hospitals = Users.query.filter_by(role='hospital').all()
    patients = Users.query.filter_by(role='patient').all()
    blood_request = Requests.query.all()
    pending_hospitals = Users.query.filter_by(role='hospital', status='Pending').all()
    return render_template('admin_dashboard.html',
        hospitals=hospitals,
        patients=patients,
        blood_request=blood_request,
        pending_hospitals=pending_hospitals
    )

@app.route('/approve_hospital/<int:user_id>', methods=['POST'])
@login_required
def approve_hospital(user_id):
    user = Users.query.get_or_404(user_id)
    user.status = 'Approved'
    db.session.commit()
    flash(f"✅ {user.username} approved!", "success")
    return redirect(url_for('manage_hospitals'))

@app.route('/reject_hospital/<int:user_id>', methods=['POST'])
@login_required
def reject_hospital(user_id):
    user = Users.query.get_or_404(user_id)
    user.status = 'Rejected'
    db.session.commit()
    flash(f"❌ {user.username} rejected.", "info")
    return redirect(url_for('manage_hospitals'))

@app.route('/view_patient', methods=['GET'])
@login_required
def view_patient():
    patients = Users.query.filter_by(role='patient').all()
    return render_template('view_patient.html', patients=patients)

@app.route('/hospital_confirm', methods=['GET'])
def hospital_confirm():
    return render_template('hospital_confirm.html')

@app.route('/manage_hospitals', methods=['GET'])
@login_required
def manage_hospitals():
    hospitals = Users.query.filter_by(role='hospital').all()
    return render_template('manage_hospitals.html', hospitals=hospitals)

@app.route('/request_blood', methods=['POST'])
@login_required
def request_blood():
    return redirect(url_for('view_hospital'))

@app.route('/delete_patient/<int:user_id>', methods=['POST'])
@login_required
def delete_patient(user_id):
    user = Users.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Patient deleted.', 'info')
    return redirect(url_for('view_patient'))

if __name__ == "__main__":
    app.run()