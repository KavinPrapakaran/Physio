import csv
import json
import math
import os
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO, StringIO
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from werkzeug.security import check_password_hash, generate_password_hash

from backend.models import (
    Assessment,
    Appointment,
    AuditLog,
    CompanySchedule,
    Invoice,
    Patient,
    PatientPackage,
    Payment,
    Permission,
    Role,
    ServicePackage,
    StaffSchedule,
    TreatmentRecord,
    User,
    db,
)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BASE_DIR = Path(__file__).resolve().parent.parent

PERMISSION_NAMES = [
    "patient_view",
    "patient_add",
    "patient_edit",
    "patient_delete",
    "appointment_view",
    "appointment_add",
    "appointment_edit",
    "appointment_cancel",
    "assessment_view",
    "assessment_add",
    "assessment_edit",
    "treatment_view",
    "treatment_add",
    "treatment_edit",
    "package_view",
    "package_add",
    "package_edit",
    "billing_view",
    "billing_add",
    "billing_edit",
    "payment_view",
    "payment_add",
    "reports_view",
    "reports_export",
    "pdf_generation",
    "whatsapp_notifications",
    "staff_management",
]

APPOINTMENT_CATEGORIES = ("Physiotherapy", "Weight Loss")


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def user_has_permission(permission_name):
    user = get_current_user()
    return bool(user and user.has_permission(permission_name))


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or not user.is_active:
            session.clear()
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return func(*args, **kwargs)

    return wrapper


def permission_required(permission_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user or not user.is_active:
                session.clear()
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if not user.has_permission(permission_name):
                flash("You do not have permission to access that feature.", "danger")
                abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_activity(user_id, action, details):
    audit = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(audit)
    db.session.commit()


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def generate_patient_id():
    last_patient = Patient.query.order_by(Patient.id.desc()).first()
    number = 1001 if last_patient is None else last_patient.id + 1001
    return f"REE{number}"


def generate_invoice_number():
    last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
    last_number = 1000 if last_invoice is None else int(last_invoice.invoice_number.split("-")[-1]) + 1
    return f"INV-{last_number}"


def ensure_database_schema():
    database_uri = db.engine.url
    if getattr(database_uri, "get_backend_name", lambda: "")() != "sqlite":
        return

    sqlite_path = database_uri.database
    if not sqlite_path:
        return

    with sqlite3.connect(sqlite_path) as connection:
        columns = connection.execute("PRAGMA table_info(assessments)").fetchall()
        column_names = {column[1] for column in columns}
        if "assessment_type" not in column_names:
            connection.execute(
                "ALTER TABLE assessments ADD COLUMN assessment_type VARCHAR(80) NOT NULL DEFAULT 'Physiotherapy Assessment'"
            )

        assessment_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(assessments)").fetchall()
        }
        assessment_column_definitions = {
            "assessment_age": "INTEGER",
            "assessment_gender": "VARCHAR(20)",
            "symptom_onset": "VARCHAR(80)",
            "aggravating_factors": "TEXT",
            "relieving_factors": "TEXT",
            "gcs_score": "INTEGER",
            "superficial_sensation": "VARCHAR(80)",
            "deep_sensation": "VARCHAR(80)",
            "reflex_right_upper_limb": "VARCHAR(80)",
            "reflex_right_lower_limb": "VARCHAR(80)",
            "reflex_left_upper_limb": "VARCHAR(80)",
            "reflex_left_lower_limb": "VARCHAR(80)",
            "reflex_muscles_examined": "TEXT",
            "muscle_strength_mmt": "VARCHAR(80)",
            "treatment_plan_entries": "TEXT",
            "tenderness": "TEXT",
            "palpation": "TEXT",
            "posture": "TEXT",
            "investigation": "TEXT",
            "problem_list": "TEXT",
            "goal": "TEXT",
        }
        for column_name, column_type in assessment_column_definitions.items():
            if column_name not in assessment_columns:
                connection.execute(
                    f"ALTER TABLE assessments ADD COLUMN {column_name} {column_type}"
                )

        treatment_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(treatment_records)").fetchall()
        }
        treatment_column_definitions = {
            "treatment_type": "VARCHAR(120)",
            "duration_minutes": "INTEGER",
            "summary": "TEXT",
            "patient_response": "TEXT",
            "next_plan": "TEXT",
        }
        for column_name, column_type in treatment_column_definitions.items():
            if column_name not in treatment_columns:
                connection.execute(
                    f"ALTER TABLE treatment_records ADD COLUMN {column_name} {column_type}"
                )

        patient_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(patients)").fetchall()
        }
        patient_column_definitions = {
            "occupation": "VARCHAR(120)",
            "referral_source": "VARCHAR(120)",
            "purpose_of_visit": "TEXT",
            "concern": "TEXT",
            "current_height": "VARCHAR(40)",
            "current_weight": "VARCHAR(40)",
            "signature": "VARCHAR(150)",
        }
        for column_name, column_type in patient_column_definitions.items():
            if column_name not in patient_columns:
                connection.execute(
                    f"ALTER TABLE patients ADD COLUMN {column_name} {column_type}"
                )

        appointment_columns = connection.execute("PRAGMA table_info(appointments)").fetchall()
        appointment_column_names = {column[1] for column in appointment_columns}
        if "appointment_category" not in appointment_column_names:
            connection.execute(
                "ALTER TABLE appointments ADD COLUMN appointment_category VARCHAR(80) NOT NULL DEFAULT 'Physiotherapy'"
            )
        if "appointment_end_time" not in appointment_column_names:
            connection.execute("ALTER TABLE appointments ADD COLUMN appointment_end_time VARCHAR(20)")

        invoice_columns = {
            column[1] for column in connection.execute("PRAGMA table_info(invoices)").fetchall()
        }
        invoice_column_definitions = {
            "discount_percentage": "FLOAT NOT NULL DEFAULT 0",
            "discount_approval_status": "VARCHAR(30) NOT NULL DEFAULT 'Not Required'",
            "discount_requested_by_id": "INTEGER",
            "discount_reviewed_by_id": "INTEGER",
            "discount_requested_at": "DATETIME",
            "discount_reviewed_at": "DATETIME",
            "discount_request_note": "TEXT",
            "discount_review_note": "TEXT",
        }
        for column_name, column_type in invoice_column_definitions.items():
            if column_name not in invoice_columns:
                connection.execute(
                    f"ALTER TABLE invoices ADD COLUMN {column_name} {column_type}"
                )
        connection.commit()


def appointment_exists(appointment_date, appointment_time, physiotherapist_name):
    return (
        Appointment.query.filter_by(
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            physiotherapist_name=physiotherapist_name,
        ).first()
        is not None
    )


def appointment_slot_available(appointment_date, start_time, end_time, physiotherapist_name, exclude_id=None):
    query = Appointment.query.filter_by(
        appointment_date=appointment_date,
        physiotherapist_name=physiotherapist_name,
    ).filter(Appointment.status.notin_(("Cancelled", "No-show")))
    if exclude_id is not None:
        query = query.filter(Appointment.id != exclude_id)

    requested_start = datetime.strptime(start_time, "%H:%M")
    requested_end = datetime.strptime(end_time, "%H:%M")
    for appointment in query.all():
        existing_start = datetime.strptime(appointment.appointment_time, "%H:%M")
        existing_end = (
            datetime.strptime(appointment.appointment_end_time, "%H:%M")
            if appointment.appointment_end_time
            else existing_start + timedelta(minutes=60)
        )
        if requested_start < existing_end and existing_start < requested_end:
            return False
    return True


def appointment_within_staff_schedule(work_date, start_time, end_time, staff_name):
    schedule = StaffSchedule.query.filter_by(staff_name=staff_name, work_date=work_date).first()
    if schedule:
        shift_start, shift_end = schedule.start_time, schedule.end_time
    else:
        company_schedule = get_company_schedule()
        shift_start, shift_end = company_schedule.default_start_time, company_schedule.default_end_time
    return start_time >= shift_start and end_time <= shift_end


def valid_time_range(start_time, end_time):
    try:
        start = datetime.strptime(start_time, "%H:%M").time()
        end = datetime.strptime(end_time, "%H:%M").time()
    except (TypeError, ValueError):
        return False
    return start < end


def get_company_schedule():
    schedule = CompanySchedule.query.get(1)
    if schedule is None:
        schedule = CompanySchedule(id=1, default_start_time="09:00", default_end_time="17:00")
        db.session.add(schedule)
        db.session.commit()
    return schedule


def get_schedule_staff_names():
    names = {
        user.full_name.strip()
        for user in User.query.filter_by(is_active=True).all()
        if user.full_name and user.full_name.strip() and (not user.role or user.role.name != "Admin")
    }
    for query in (
        db.session.query(Appointment.physiotherapist_name).distinct(),
        db.session.query(TreatmentRecord.physiotherapist_name).distinct(),
        db.session.query(StaffSchedule.staff_name).distinct(),
    ):
        names.update(
            value.strip()
            for (value,) in query.all()
            if value and value.strip()
        )
    return sorted(names, key=str.casefold)


def build_staff_schedule(work_date):
    company_schedule = get_company_schedule()
    staff_names = get_schedule_staff_names()
    saved_schedules = {
        item.staff_name: item
        for item in StaffSchedule.query.filter_by(work_date=work_date).all()
    }
    appointments = (
        Appointment.query.filter_by(appointment_date=work_date)
        .filter(Appointment.status.notin_(("Cancelled", "No-show")))
        .order_by(Appointment.appointment_time.asc())
        .all()
    )
    now = datetime.now()
    now_time = now.strftime("%H:%M")
    result = []
    for staff_name in staff_names:
        saved_schedule = saved_schedules.get(staff_name)
        start_time = saved_schedule.start_time if saved_schedule else company_schedule.default_start_time
        end_time = saved_schedule.end_time if saved_schedule else company_schedule.default_end_time
        staff_appointments = [
            appointment for appointment in appointments
            if appointment.physiotherapist_name.casefold() == staff_name.casefold()
        ]
        current_appointment = None
        if work_date == now.date():
            for appointment in staff_appointments:
                appointment_start = datetime.strptime(appointment.appointment_time, "%H:%M")
                appointment_end = (
                    datetime.strptime(appointment.appointment_end_time, "%H:%M")
                    if appointment.appointment_end_time
                    else appointment_start + timedelta(minutes=60)
                )
                current_time = datetime.strptime(now_time, "%H:%M")
                if appointment_start <= current_time < appointment_end:
                    current_appointment = appointment
                    break
        if work_date != now.date() or now_time < start_time or now_time >= end_time:
            availability = "Off shift"
        elif current_appointment:
            availability = f"With {current_appointment.patient_name}"
        else:
            availability = "Available"
        result.append(
            {
                "staff_name": staff_name,
                "start_time": start_time,
                "end_time": end_time,
                "uses_company_default": saved_schedule.uses_company_default if saved_schedule else True,
                "availability": availability,
                "appointments": [
                    {
                        "patient_name": appointment.patient_name,
                        "start_time": appointment.appointment_time,
                        "end_time": appointment.appointment_end_time or "",
                        "status": appointment.status,
                    }
                    for appointment in staff_appointments
                ],
            }
        )
    return result


def compute_dashboard_stats():
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    weekly_start = today - timedelta(days=6)
    first_month_index = today.year * 12 + today.month - 1 - 11
    first_month_year, first_month_offset = divmod(first_month_index, 12)
    monthly_start = datetime(first_month_year, first_month_offset + 1, 1).date()

    payment_totals = (
        db.session.query(Payment.payment_date, db.func.sum(Payment.amount))
        .filter(Payment.payment_date >= monthly_start, Payment.payment_date <= today)
        .group_by(Payment.payment_date)
        .all()
    )
    revenue_by_date = {payment_date: total or 0 for payment_date, total in payment_totals}

    weekly_revenue = [
        {
            "label": (weekly_start + timedelta(days=offset)).strftime("%a"),
            "value": revenue_by_date.get(weekly_start + timedelta(days=offset), 0),
            "date": (weekly_start + timedelta(days=offset)).isoformat(),
        }
        for offset in range(7)
    ]
    monthly_revenue = []
    for offset in range(12):
        month_index = first_month_index + offset
        year, month_offset = divmod(month_index, 12)
        month_date = datetime(year, month_offset + 1, 1).date()
        monthly_revenue.append(
            {
                "label": month_date.strftime("%b"),
                "value": sum(
                    amount
                    for payment_date, amount in revenue_by_date.items()
                    if payment_date.year == year and payment_date.month == month_offset + 1
                ),
                "date": month_date.strftime("%B %Y"),
            }
        )

    for revenue_series in (weekly_revenue, monthly_revenue):
        maximum = max((item["value"] for item in revenue_series), default=0)
        for item in revenue_series:
            item["height"] = item["value"] / maximum * 100 if maximum else 0

    stats = {
        "total_patients": Patient.query.count(),
        "today_appointments": Appointment.query.filter(Appointment.appointment_date == today).count(),
        "upcoming_appointments": Appointment.query.filter(Appointment.appointment_date >= today).count(),
        "completed_appointments": Appointment.query.filter_by(status="Completed").count(),
        "cancelled_appointments": Appointment.query.filter_by(status="Cancelled").count(),
        "active_packages": PatientPackage.query.filter(PatientPackage.remaining_sessions > 0).count(),
        "pending_payments": Invoice.query.filter(Invoice.balance_amount > 0).count(),
        "todays_revenue": db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(Payment.payment_date == today).scalar() or 0,
        "monthly_revenue": db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).filter(Payment.payment_date >= month_start).scalar() or 0,
        "new_patients": Patient.query.filter(Patient.registration_date >= datetime.combine(month_start, datetime.min.time())).count(),
        "followups": Appointment.query.filter(Appointment.status == "Confirmed").count(),
    }
    return stats, weekly_revenue, monthly_revenue


def update_patient_package_usage(patient_id):
    patient_packages = PatientPackage.query.filter_by(patient_id=patient_id).all()
    for package_record in patient_packages:
        used = TreatmentRecord.query.filter_by(patient_id=patient_id).count()
        package_record.used_sessions = used
        package_record.remaining_sessions = max(package_record.total_sessions - used, 0)
        if package_record.remaining_sessions <= 0:
            package_record.payment_status = "Completed"
    db.session.commit()


def get_treatment_staff_names():
    treatment_names = db.session.query(TreatmentRecord.physiotherapist_name).filter(
        TreatmentRecord.physiotherapist_name.isnot(None),
        TreatmentRecord.physiotherapist_name != "",
    ).distinct().all()
    active_staff = User.query.filter_by(is_active=True).with_entities(User.full_name).all()
    return sorted(
        {name.strip() for (name,) in treatment_names + active_staff if name and name.strip()},
        key=str.casefold,
    )


def generate_assessment_pdf(assessment):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title="REE Forma Assessment")
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("REE Forma - Physiotherapy Assessment", styles["Title"]))
    story.append(Paragraph(f"Patient: {assessment.patient_name}", styles["Heading2"]))
    story.append(Paragraph(f"Patient ID: {assessment.patient.patient_id if assessment.patient else ''}", styles["Normal"]))
    story.append(Paragraph(f"Phone: {assessment.patient.phone if assessment.patient and assessment.patient.phone else ''}", styles["Normal"]))
    story.append(Paragraph(f"Age: {assessment.assessment_age if assessment.assessment_age is not none else ''}", styles["Normal"]))
    story.append(Paragraph(f"Gender: {assessment.assessment_gender or ''}", styles["Normal"]))
    story.append(Paragraph(f"Date: {assessment.assessment_date.date() if assessment.assessment_date else ''}", styles["Normal"]))
    story.append(Spacer(1, 12))
    for title, value in [
        ("Symptoms", ""),
        ("Site", assessment.pain_location),
        ("Onset", assessment.symptom_onset),
        ("Duration", assessment.pain_duration),
        ("Type", assessment.pain_type),
        ("Pain Intensity (0-10)", assessment.pain_intensity),
        ("Aggravating Factors", assessment.aggravating_factors),
        ("Relieving Factors", assessment.relieving_factors),
        ("Higher Functions", ""),
        ("GCS", assessment.gcs_score),
        ("Superficial Sensation", assessment.superficial_sensation),
        ("Deep Sensation", assessment.deep_sensation),
        ("Right Reflex - Upper Limb", assessment.reflex_right_upper_limb),
        ("Right Reflex - Lower Limb", assessment.reflex_right_lower_limb),
        ("Left Reflex - Upper Limb", assessment.reflex_left_upper_limb),
        ("Left Reflex - Lower Limb", assessment.reflex_left_lower_limb),
        ("Muscles Examined", assessment.reflex_muscles_examined),
        ("Muscle Strength MMT", assessment.muscle_strength_mmt),
        ("Muscle Strength Findings", assessment.muscle_strength),
        ("Tenderness", assessment.tenderness),
        ("Palpation", assessment.palpation),
        ("Posture", assessment.posture),
        ("Investigation", assessment.investigation),
        ("Problem List", assessment.problem_list),
        ("Goal", assessment.goal),
        ("Chief Complaint", assessment.chief_complaint),
        ("Present History", assessment.present_history),
        ("Clinical Findings", assessment.clinical_findings),
        ("Diagnosis", assessment.diagnosis),
        ("Recommendations", assessment.recommendations),
    ]:
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
        story.append(Paragraph(str(value) if value not in (None, "") else "—", styles["Normal"]))
        story.append(Spacer(1, 8))
    if assessment.treatment_plan_entries:
        story.append(Paragraph("Treatment Plan Schedule", styles["Heading3"]))
        for index, entry in enumerate(json.loads(assessment.treatment_plan_entries), start=1):
            story.append(
                Paragraph(
                    f"{index}. {entry.get('treatment', '') or '-'} | {entry.get('date', '') or '-'}",
                    styles["Normal"],
                )
            )
            story.append(Spacer(1, 4))
    doc.build(story)
    buffer.seek(0)
    return buffer


def ensure_default_system_data():
    for role_name, description in [("Admin", "Full access to the system."), ("Staff", "Default limited staff role.")]:
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(name=role_name, description=description)
            db.session.add(role)
    db.session.commit()

    for permission_name in PERMISSION_NAMES:
        permission = Permission.query.filter_by(name=permission_name).first()
        if permission is None:
            db.session.add(Permission(name=permission_name, description=f"Allows access to {permission_name}"))
    db.session.commit()

    admin_role = Role.query.filter_by(name="Admin").first()
    if admin_role:
        admin_role.permissions = list(Permission.query.all())

    staff_role = Role.query.filter_by(name="Staff").first()
    if staff_role:
        default_staff_permissions = [
            "patient_view",
            "patient_add",
            "patient_edit",
            "appointment_view",
            "appointment_add",
            "appointment_edit",
            "assessment_view",
            "assessment_add",
            "assessment_edit",
            "treatment_view",
            "treatment_add",
            "treatment_edit",
            "package_view",
            "billing_view",
            "payment_view",
            "reports_view",
        ]
        staff_role.permissions = []
        for perm_name in default_staff_permissions:
            permission = Permission.query.filter_by(name=perm_name).first()
            if permission is not None:
                staff_role.permissions.append(permission)

    db.session.commit()

    if User.query.filter_by(username="admin").first() is None:
        admin_user = User(
            username="admin",
            full_name="System Administrator",
            password_hash=generate_password_hash("admin123"),
            role_id=admin_role.id,
            is_active=True,
        )
        db.session.add(admin_user)
        db.session.commit()


def create_app():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "ree-forma-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'ree_forma.db'}")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": get_current_user(),
            "has_permission": user_has_permission,
            "permission_names": PERMISSION_NAMES,
        }

    with app.app_context():
        db.create_all()
        ensure_database_schema()
        ensure_default_system_data()

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.is_active and check_password_hash(user.password_hash, password):
                session["user_id"] = user.id
                log_activity(user.id, "Login", "Successful login")
                flash("Login successful.", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid username or password.", "danger")
            return render_template("login.html")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        user = get_current_user()
        if user:
            log_activity(user.id, "Logout", "User logged out")
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        stats, weekly_revenue, monthly_revenue = compute_dashboard_stats()
        return render_template(
            "dashboard.html",
            stats=stats,
            weekly_revenue=weekly_revenue,
            monthly_revenue=monthly_revenue,
        )

    @app.route("/patients")
    @login_required
    @permission_required("patient_view")
    def patients():
        q = request.args.get("q", "").strip()
        query = Patient.query
        if q:
            query = query.filter((Patient.full_name.ilike(f"%{q}%")) | (Patient.patient_id.ilike(f"%{q}%")) | (Patient.phone.ilike(f"%{q}%")))
        patients = query.order_by(Patient.created_at.desc()).all()
        return render_template("patients.html", patients=patients, query=q)

    @app.route("/patients/new", methods=["GET", "POST"])
    @login_required
    @permission_required("patient_add")
    def new_patient():
        if request.method == "POST":
            patient_id = request.form.get("patient_id", "").strip() or generate_patient_id()
            if Patient.query.filter_by(patient_id=patient_id).first():
                patient_id = generate_patient_id()
            purposes = [
                purpose
                for purpose in request.form.getlist("purpose_of_visit")
                if purpose in ("Physiotherapy", "Weight Loss")
            ]
            patient = Patient(
                patient_id=patient_id,
                full_name=request.form.get("full_name").strip(),
                dob=parse_date(request.form.get("dob")),
                gender=request.form.get("gender"),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                address=request.form.get("address", "").strip(),
                occupation=request.form.get("occupation", "").strip(),
                referral_source=request.form.get("referral_source", "").strip(),
                purpose_of_visit=", ".join(purposes),
                concern=request.form.get("concern", "").strip(),
                current_height=request.form.get("current_height", "").strip(),
                current_weight=request.form.get("current_weight", "").strip(),
                signature=request.form.get("signature", "").strip(),
                emergency_contact=request.form.get("emergency_contact", "").strip(),
                medical_history=request.form.get("medical_history", "").strip(),
                existing_conditions=request.form.get("existing_conditions", "").strip(),
                allergies=request.form.get("allergies", "").strip(),
                referring_doctor=request.form.get("referring_doctor", "").strip(),
                registration_date=datetime.utcnow(),
            )
            db.session.add(patient)
            db.session.commit()
            log_activity(session["user_id"], "Patient created", f"Created patient {patient.full_name}")
            flash("Patient created successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient.id))
        return render_template(
            "patient_form.html",
            patient=None,
            form_title="Personal Details Form",
            current_date=datetime.utcnow().date().isoformat(),
        )

    @app.route("/patients/<int:patient_id>")
    @login_required
    @permission_required("patient_view")
    def patient_detail(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        patient_age = None
        if patient.dob:
            today = datetime.utcnow().date()
            patient_age = today.year - patient.dob.year - (
                (today.month, today.day) < (patient.dob.month, patient.dob.day)
            )
        appointments = Appointment.query.filter_by(patient_id=patient.id).order_by(Appointment.appointment_date.desc()).all()
        assessments = Assessment.query.filter_by(patient_id=patient.id).order_by(Assessment.assessment_date.desc()).all()
        treatments = TreatmentRecord.query.filter_by(patient_id=patient.id).order_by(TreatmentRecord.date.desc()).all()
        invoices = Invoice.query.filter_by(patient_id=patient.id).order_by(Invoice.invoice_date.desc()).all()
        packages = PatientPackage.query.filter_by(patient_id=patient.id).order_by(PatientPackage.start_date.desc()).all()
        return render_template(
            "patient_detail.html",
            patient=patient,
            patient_age=patient_age,
            appointments=appointments,
            assessments=assessments,
            treatments=treatments,
            invoices=invoices,
            packages=packages,
        )

    @app.route("/patients/<int:patient_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("patient_edit")
    def edit_patient(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        if request.method == "POST":
            purposes = [
                purpose
                for purpose in request.form.getlist("purpose_of_visit")
                if purpose in ("Physiotherapy", "Weight Loss")
            ]
            patient.full_name = request.form.get("full_name").strip()
            patient.dob = parse_date(request.form.get("dob"))
            patient.gender = request.form.get("gender")
            patient.phone = request.form.get("phone", "").strip()
            patient.email = request.form.get("email", "").strip()
            patient.address = request.form.get("address", "").strip()
            patient.occupation = request.form.get("occupation", "").strip()
            patient.referral_source = request.form.get("referral_source", "").strip()
            patient.purpose_of_visit = ", ".join(purposes)
            patient.concern = request.form.get("concern", "").strip()
            patient.current_height = request.form.get("current_height", "").strip()
            patient.current_weight = request.form.get("current_weight", "").strip()
            patient.signature = request.form.get("signature", "").strip()
            patient.emergency_contact = request.form.get("emergency_contact", "").strip()
            patient.medical_history = request.form.get("medical_history", "").strip()
            patient.existing_conditions = request.form.get("existing_conditions", "").strip()
            patient.allergies = request.form.get("allergies", "").strip()
            patient.referring_doctor = request.form.get("referring_doctor", "").strip()
            db.session.commit()
            log_activity(session["user_id"], "Patient updated", f"Updated patient {patient.full_name}")
            flash("Patient updated successfully.", "success")
            return redirect(url_for("patient_detail", patient_id=patient.id))
        return render_template(
            "patient_form.html",
            patient=patient,
            form_title="Edit Personal Details Form",
            current_date=patient.registration_date.date().isoformat() if patient.registration_date else "",
        )

    @app.route("/patients/<int:patient_id>/delete", methods=["POST"])
    @login_required
    @permission_required("patient_delete")
    def delete_patient(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        db.session.delete(patient)
        db.session.commit()
        log_activity(session["user_id"], "Patient deleted", f"Deleted patient {patient.full_name}")
        flash("Patient deleted.", "warning")
        return redirect(url_for("patients"))

    @app.route("/appointments")
    @login_required
    @permission_required("appointment_view")
    def appointments():
        status_filter = request.args.get("status", "")
        category_filter = request.args.get("category", "")
        selected_date = parse_date(request.args.get("date", ""))
        query = Appointment.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        if category_filter in APPOINTMENT_CATEGORIES:
            query = query.filter_by(appointment_category=category_filter)
        if selected_date:
            query = query.filter_by(appointment_date=selected_date)
        appointments = query.order_by(Appointment.appointment_date.asc(), Appointment.appointment_time.asc()).all()
        schedule_date = parse_date(request.args.get("schedule_date", "")) or datetime.now().date()
        company_schedule = get_company_schedule()
        return render_template(
            "appointments.html",
            appointments=appointments,
            status_filter=status_filter,
            category_filter=category_filter,
            appointment_categories=APPOINTMENT_CATEGORIES,
            selected_date=selected_date.isoformat() if selected_date else "",
            schedule_date=schedule_date.isoformat(),
            schedule_data=build_staff_schedule(schedule_date),
            company_schedule=company_schedule,
            is_admin=bool(get_current_user().role and get_current_user().role.name == "Admin"),
        )

    @app.route("/appointments/schedule/data")
    @login_required
    @permission_required("appointment_view")
    def staff_schedule_data():
        work_date = parse_date(request.args.get("date", ""))
        if work_date is None:
            abort(400)
        return jsonify({"date": work_date.isoformat(), "staff": build_staff_schedule(work_date)})

    @app.route("/appointments/schedule", methods=["POST"])
    @login_required
    @permission_required("appointment_view")
    def save_staff_schedule():
        user = get_current_user()
        is_admin = bool(user.role and user.role.name == "Admin")
        action = request.form.get("action", "save-custom")
        if action == "save-company-default":
            if not is_admin:
                abort(403)
            start_time = request.form.get("default_start_time", "")
            end_time = request.form.get("default_end_time", "")
            if not valid_time_range(start_time, end_time):
                flash("Enter a valid company start and end time.", "danger")
                return redirect(url_for("appointments"))
            company_schedule = get_company_schedule()
            company_schedule.default_start_time = start_time
            company_schedule.default_end_time = end_time
            StaffSchedule.query.filter_by(uses_company_default=True).update(
                {"start_time": start_time, "end_time": end_time},
                synchronize_session=False,
            )
            db.session.commit()
            flash("Company default hours updated.", "success")
            return redirect(url_for("appointments", schedule_date=request.form.get("work_date", "")))

        staff_name = request.form.get("staff_name", "").strip()
        work_date = parse_date(request.form.get("work_date", ""))
        if not staff_name or work_date is None:
            abort(400)
        if not is_admin and staff_name.casefold() != user.full_name.casefold():
            abort(403)

        schedule = StaffSchedule.query.filter_by(staff_name=staff_name, work_date=work_date).first()
        if action == "use-company-default":
            company_schedule = get_company_schedule()
            start_time = company_schedule.default_start_time
            end_time = company_schedule.default_end_time
            uses_company_default = True
        else:
            start_time = request.form.get("start_time", "")
            end_time = request.form.get("end_time", "")
            if not valid_time_range(start_time, end_time):
                flash("End time must be later than the start time.", "danger")
                return redirect(url_for("appointments", schedule_date=work_date.isoformat()))
            uses_company_default = False

        if schedule is None:
            schedule = StaffSchedule(staff_name=staff_name, work_date=work_date)
            db.session.add(schedule)
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.uses_company_default = uses_company_default
        db.session.commit()
        flash(f"Schedule updated for {staff_name}.", "success")
        return redirect(url_for("appointments", schedule_date=work_date.isoformat()))

    @app.route("/appointments/export")
    @login_required
    @permission_required("appointment_view")
    def export_appointments():
        export_date = parse_date(request.args.get("date", ""))
        if export_date is None:
            abort(400)
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Date", "Start", "End", "Patient", "Category", "Staff", "Type", "Status", "Notes"])
        rows = Appointment.query.filter_by(appointment_date=export_date).order_by(
            Appointment.appointment_time.asc()
        ).all()
        for appointment in rows:
            writer.writerow([
                appointment.appointment_date.isoformat(),
                appointment.appointment_time,
                appointment.appointment_end_time or "",
                appointment.patient_name,
                appointment.appointment_category,
                appointment.physiotherapist_name,
                appointment.appointment_type,
                appointment.status,
                appointment.notes or "",
            ])
        return send_file(
            BytesIO(output.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"appointments-{export_date.isoformat()}.csv",
        )

    @app.route("/appointments/new", methods=["GET", "POST"])
    @login_required
    @permission_required("appointment_add")
    def new_appointment():
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            appointment_category = request.form.get("appointment_category", "Physiotherapy")
            if appointment_category not in APPOINTMENT_CATEGORIES:
                abort(400)
            date_value = parse_date(request.form.get("appointment_date"))
            time_value = request.form.get("appointment_time")
            end_time_value = request.form.get("appointment_end_time", "").strip()
            physio = request.form.get("physiotherapist_name").strip()
            if date_value is None or not valid_time_range(time_value, end_time_value):
                flash("Enter a valid appointment date and end time after the start time.", "danger")
                return redirect(url_for("new_appointment"))
            if not appointment_slot_available(date_value, time_value, end_time_value, physio):
                flash("This staff member already has an appointment during that time.", "danger")
                return redirect(url_for("new_appointment"))
            if not appointment_within_staff_schedule(date_value, time_value, end_time_value, physio):
                flash("This appointment falls outside the staff member's working hours.", "danger")
                return redirect(url_for("new_appointment"))
            appointment = Appointment(
                patient_id=patient.id,
                patient_name=patient.full_name,
                physiotherapist_name=physio,
                appointment_date=date_value,
                appointment_time=time_value,
                appointment_end_time=end_time_value,
                appointment_category=appointment_category,
                appointment_type=request.form.get("appointment_type"),
                notes=request.form.get("notes").strip(),
                status=request.form.get("status", "Scheduled"),
            )
            db.session.add(appointment)
            db.session.commit()
            log_activity(session["user_id"], "Appointment created", f"Created appointment for {patient.full_name}")
            flash("Appointment created successfully.", "success")
            return redirect(url_for("appointments"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template(
            "appointment_form.html",
            appointment=None,
            patients=patients,
            form_title="Add Appointment",
            appointment_categories=APPOINTMENT_CATEGORIES,
            physiotherapists=get_schedule_staff_names(),
        )

    @app.route("/appointments/<int:appointment_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("appointment_edit")
    def edit_appointment(appointment_id):
        appointment = Appointment.query.get_or_404(appointment_id)
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            appointment_category = request.form.get("appointment_category", "Physiotherapy")
            if appointment_category not in APPOINTMENT_CATEGORIES:
                abort(400)
            appointment.patient_id = patient.id
            appointment.patient_name = patient.full_name
            appointment.physiotherapist_name = request.form.get("physiotherapist_name").strip()
            appointment.appointment_date = parse_date(request.form.get("appointment_date"))
            appointment.appointment_time = request.form.get("appointment_time")
            appointment_end_time = request.form.get("appointment_end_time", "").strip()
            if appointment.appointment_date is None or not valid_time_range(appointment.appointment_time, appointment_end_time):
                flash("Enter a valid appointment date and end time after the start time.", "danger")
                return redirect(url_for("edit_appointment", appointment_id=appointment.id))
            if not appointment_slot_available(
                appointment.appointment_date,
                appointment.appointment_time,
                appointment_end_time,
                appointment.physiotherapist_name,
                exclude_id=appointment.id,
            ):
                flash("This staff member already has an appointment during that time.", "danger")
                return redirect(url_for("edit_appointment", appointment_id=appointment.id))
            if not appointment_within_staff_schedule(
                appointment.appointment_date,
                appointment.appointment_time,
                appointment_end_time,
                appointment.physiotherapist_name,
            ):
                flash("This appointment falls outside the staff member's working hours.", "danger")
                return redirect(url_for("edit_appointment", appointment_id=appointment.id))
            appointment.appointment_end_time = appointment_end_time
            appointment.appointment_category = appointment_category
            appointment.appointment_type = request.form.get("appointment_type")
            appointment.notes = request.form.get("notes").strip()
            appointment.status = request.form.get("status")
            db.session.commit()
            log_activity(session["user_id"], "Appointment updated", f"Updated appointment for {appointment.patient_name}")
            flash("Appointment updated successfully.", "success")
            return redirect(url_for("appointments"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template(
            "appointment_form.html",
            appointment=appointment,
            patients=patients,
            form_title="Edit Appointment",
            appointment_categories=APPOINTMENT_CATEGORIES,
            physiotherapists=get_schedule_staff_names(),
        )

    @app.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
    @login_required
    @permission_required("appointment_cancel")
    def cancel_appointment(appointment_id):
        appointment = Appointment.query.get_or_404(appointment_id)
        appointment.status = "Cancelled"
        db.session.commit()
        log_activity(session["user_id"], "Appointment cancelled", f"Cancelled appointment for {appointment.patient_name}")
        flash("Appointment cancelled.", "warning")
        return redirect(url_for("appointments"))

    @app.route("/assessments")
    @login_required
    @permission_required("assessment_view")
    def assessments():
        assessments = Assessment.query.order_by(Assessment.assessment_date.desc()).all()
        return render_template("assessments.html", assessments=assessments)

    @app.route("/assessments/new", methods=["GET", "POST"])
    @login_required
    @permission_required("assessment_add")
    def new_assessment():
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            assessment_date_value = parse_date(request.form.get("assessment_date"))
            assessment_date = (
                datetime.combine(assessment_date_value, datetime.min.time())
                if assessment_date_value
                else datetime.utcnow()
            )
            assessment_age = None
            if patient.dob:
                age_date = assessment_date.date()
                assessment_age = age_date.year - patient.dob.year - (
                    (age_date.month, age_date.day) < (patient.dob.month, patient.dob.day)
                )
            gcs_score_value = request.form.get("gcs_score", "").strip()
            if gcs_score_value and (
                not gcs_score_value.isdigit() or not 3 <= int(gcs_score_value) <= 15
            ):
                abort(400)
            treatment_values = request.form.getlist("treatment_plan_treatment[]")
            treatment_dates = request.form.getlist("treatment_plan_date[]")
            treatment_plan_entries = []
            for index, treatment_value in enumerate(treatment_values):
                treatment = treatment_value.strip()
                treatment_date = treatment_dates[index].strip() if index < len(treatment_dates) else ""
                if treatment or treatment_date:
                    treatment_plan_entries.append({"treatment": treatment, "date": treatment_date})
            assessment = Assessment(
                patient_id=patient.id,
                patient_name=patient.full_name,
                assessment_age=assessment_age,
                assessment_gender=patient.gender or "",
                assessment_date=assessment_date,
                assessment_type=request.form.get("assessment_type", "Physiotherapy Assessment").strip() or "Physiotherapy Assessment",
                chief_complaint=request.form.get("chief_complaint").strip(),
                present_history=request.form.get("present_history").strip(),
                past_medical_history=request.form.get("past_medical_history").strip(),
                surgical_history=request.form.get("surgical_history").strip(),
                medication=request.form.get("medication").strip(),
                pain_location=request.form.get("pain_location").strip(),
                symptom_onset=request.form.get("symptom_onset", "").strip(),
                pain_intensity=request.form.get("pain_intensity").strip(),
                pain_duration=request.form.get("pain_duration").strip(),
                pain_type=request.form.get("pain_type").strip(),
                aggravating_factors=request.form.get("aggravating_factors", "").strip(),
                relieving_factors=request.form.get("relieving_factors", "").strip(),
                gcs_score=int(gcs_score_value) if gcs_score_value else None,
                superficial_sensation=request.form.get("superficial_sensation", "").strip(),
                deep_sensation=request.form.get("deep_sensation", "").strip(),
                reflex_right_upper_limb=request.form.get("reflex_right_upper_limb", "").strip(),
                reflex_right_lower_limb=request.form.get("reflex_right_lower_limb", "").strip(),
                reflex_left_upper_limb=request.form.get("reflex_left_upper_limb", "").strip(),
                reflex_left_lower_limb=request.form.get("reflex_left_lower_limb", "").strip(),
                reflex_muscles_examined=request.form.get("reflex_muscles_examined", "").strip(),
                posture_assessment=request.form.get("posture_assessment", "").strip(),
                range_of_motion=request.form.get("range_of_motion", "").strip(),
                muscle_strength=request.form.get("muscle_strength", "").strip(),
                muscle_strength_mmt=request.form.get("muscle_strength_mmt", "").strip(),
                tenderness=request.form.get("tenderness", "").strip(),
                palpation=request.form.get("palpation", "").strip(),
                posture=request.form.get("posture", "").strip(),
                investigation=request.form.get("investigation", "").strip(),
                problem_list=request.form.get("problem_list", "").strip(),
                goal=request.form.get("goal", "").strip(),
                flexibility=request.form.get("flexibility", "").strip(),
                balance=request.form.get("balance", "").strip(),
                gait_assessment=request.form.get("gait_analysis", "").strip(),
                functional_assessment=request.form.get("functional_assessment", "").strip(),
                neurological_assessment=request.form.get("neurological_assessment", "").strip(),
                special_tests=request.form.get("special_tests", "").strip(),
                clinical_findings=request.form.get("clinical_findings", "").strip(),
                diagnosis=request.form.get("diagnosis", "").strip(),
                treatment_goals=request.form.get("treatment_goals", "").strip(),
                short_term_goals=request.form.get("short_term_goals", "").strip(),
                long_term_goals=request.form.get("long_term_goals", "").strip(),
                treatment_plan=request.form.get("treatment_plan", "").strip(),
                treatment_plan_entries=json.dumps(treatment_plan_entries),
                physiotherapist_notes=request.form.get("physiotherapist_notes", "").strip(),
                recommendations=request.form.get("recommendations", "").strip(),
                follow_up_date=parse_date(request.form.get("follow_up_date")),
            )
            db.session.add(assessment)
            db.session.commit()
            log_activity(session["user_id"], "Assessment created", f"Assessment created for {patient.full_name}")
            flash("Assessment saved successfully.", "success")
            return redirect(url_for("assessments"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template("assessment_form.html", assessment=None, patients=patients)

    @app.route("/assessments/<int:assessment_id>")
    @login_required
    @permission_required("assessment_view")
    def assessment_detail(assessment_id):
        assessment = Assessment.query.get_or_404(assessment_id)
        treatment_plan_entries = json.loads(assessment.treatment_plan_entries or "[]")
        return render_template(
            "assessment_detail.html",
            assessment=assessment,
            treatment_plan_entries=treatment_plan_entries,
        )

    @app.route("/assessments/<int:assessment_id>/pdf")
    @login_required
    @permission_required("pdf_generation")
    def assessment_pdf(assessment_id):
        assessment = Assessment.query.get_or_404(assessment_id)
        pdf_buffer = generate_assessment_pdf(assessment)
        return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=f"REE_Forma_Assessment_{assessment.id}.pdf")

    @app.route("/treatments")
    @login_required
    @permission_required("treatment_view")
    def treatments():
        treatment_list = TreatmentRecord.query.order_by(TreatmentRecord.date.desc()).all()
        return render_template("treatments.html", treatments=treatment_list)

    @app.route("/treatments/<int:treatment_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("treatment_edit")
    def edit_treatment(treatment_id):
        treatment = TreatmentRecord.query.get_or_404(treatment_id)
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            treatment.patient_id = patient.id
            treatment.patient_name = patient.full_name
            treatment.date = parse_date(request.form.get("date"))
            treatment.physiotherapist_name = request.form.get("physiotherapist_name", request.form.get("Staff", "")).strip()
            treatment.treatment_type = request.form.get("treatment_type", "").strip()
            duration_value = request.form.get("duration", "").strip()
            treatment.duration_minutes = int(duration_value) if duration_value.isdigit() else None
            treatment.summary = request.form.get("summary", "").strip()
            treatment.treatment_performed = request.form.get("treatment", request.form.get("treatment_performed", "")).strip()
            treatment.patient_response = request.form.get("patient_response", "").strip()
            treatment.next_plan = request.form.get("next_plan", "").strip()
            treatment.exercises = request.form.get("exercises", "").strip()
            treatment.therapy_techniques = request.form.get("therapy_techniques", "").strip()
            treatment.pain_before = request.form.get("pain_before", "").strip()
            treatment.pain_after = request.form.get("pain_after", "").strip()
            treatment.progress = request.form.get("progress", "").strip()
            treatment.notes = request.form.get("notes", "").strip()
            treatment.next_appointment = parse_date(request.form.get("next_appointment"))
            treatment.follow_up_instructions = request.form.get("follow_up_instructions", "").strip()
            db.session.commit()
            log_activity(session["user_id"], "Treatment updated", f"Updated treatment for {patient.full_name}")
            flash("Treatment updated successfully.", "success")
            return redirect(url_for("treatments"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template(
            "treatment_form.html",
            patients=patients,
            treatment=treatment,
            form_title="Edit Treatment",
            staff_names=get_treatment_staff_names(),
        )

    @app.route("/treatments/new", methods=["GET", "POST"])
    @login_required
    @permission_required("treatment_add")
    def new_treatment():
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            treatment = TreatmentRecord(
                patient_id=patient.id,
                patient_name=patient.full_name,
                date=parse_date(request.form.get("date")),
                physiotherapist_name=request.form.get("physiotherapist_name", request.form.get("Staff", "")).strip(),
                treatment_type=request.form.get("treatment_type", "").strip(),
                duration_minutes=int(request.form.get("duration", "")) if request.form.get("duration", "").isdigit() else None,
                summary=request.form.get("summary", "").strip(),
                treatment_performed=request.form.get("treatment", request.form.get("treatment_performed", "")).strip(),
                patient_response=request.form.get("patient_response", "").strip(),
                next_plan=request.form.get("next_plan", "").strip(),
                exercises=request.form.get("exercises", "").strip(),
                therapy_techniques=request.form.get("therapy_techniques", "").strip(),
                pain_before=request.form.get("pain_before", "").strip(),
                pain_after=request.form.get("pain_after", "").strip(),
                progress=request.form.get("progress", "").strip(),
                notes=request.form.get("notes", "").strip(),
                next_appointment=parse_date(request.form.get("next_appointment")),
                follow_up_instructions=request.form.get("follow_up_instructions", "").strip(),
            )
            db.session.add(treatment)
            db.session.commit()
            update_patient_package_usage(patient.id)
            log_activity(session["user_id"], "Treatment created", f"Created treatment for {patient.full_name}")
            flash("Treatment saved successfully.", "success")
            return redirect(url_for("treatments"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template(
            "treatment_form.html",
            patients=patients,
            treatment=None,
            form_title="Add Treatment",
            staff_names=get_treatment_staff_names(),
        )

    @app.route("/packages")
    @login_required
    @permission_required("package_view")
    def packages():
        packages_list = ServicePackage.query.order_by(ServicePackage.name.asc()).all()
        patient_packages = PatientPackage.query.order_by(PatientPackage.start_date.desc()).all()
        return render_template("packages.html", packages=packages_list, patient_packages=patient_packages)

    @app.route("/packages/new", methods=["GET", "POST"])
    @login_required
    @permission_required("package_add")
    def new_package():
        if request.method == "POST":
            package = ServicePackage(
                name=request.form.get("name").strip(),
                session_count=int(request.form.get("session_count") or 0),
                price=float(request.form.get("price") or 0.0),
                validity_days=int(request.form.get("validity_days") or 30),
                included_services=request.form.get("description").strip() or request.form.get("included_services", "").strip(),
            )
            db.session.add(package)
            db.session.commit()
            log_activity(session["user_id"], "Package created", f"Created package {package.name}")
            flash("Package created successfully.", "success")
            return redirect(url_for("packages"))
        return render_template("package_form.html", package=None, form_title="Add Package")

    @app.route("/packages/<int:package_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("package_edit")
    def edit_package(package_id):
        package = ServicePackage.query.get_or_404(package_id)
        if request.method == "POST":
            package.name = request.form.get("name").strip()
            package.session_count = int(request.form.get("session_count") or 0)
            package.price = float(request.form.get("price") or 0.0)
            package.validity_days = int(request.form.get("validity_days") or 30)
            package.included_services = request.form.get("description").strip()
            db.session.commit()
            log_activity(session["user_id"], "Package updated", f"Updated package {package.name}")
            flash("Package updated successfully.", "success")
            return redirect(url_for("packages"))
        return render_template("package_form.html", package=package, form_title="Edit Package")

    @app.route("/billing")
    @login_required
    @permission_required("billing_view")
    def billing():
        invoices = Invoice.query.order_by(Invoice.invoice_date.desc()).all()
        billable_invoices = [
            item for item in invoices
            if item.discount_approval_status != "Pending" and item.status != "Discount Rejected"
        ]
        total_revenue = sum(item.total_amount for item in billable_invoices)
        pending = sum(item.balance_amount for item in invoices)
        user = get_current_user()
        return render_template(
            "billing.html",
            invoices=invoices,
            total_revenue=total_revenue,
            pending=pending,
            is_admin=bool(user.role and user.role.name == "Admin"),
        )

    @app.route("/billing/new", methods=["GET", "POST"])
    @login_required
    @permission_required("billing_add")
    def new_invoice():
        if request.method == "POST":
            patient = Patient.query.get_or_404(request.form.get("patient_id"))
            try:
                total = float(request.form.get("total_amount") or 0)
                discount_percentage = float(request.form.get("discount_percentage") or 0)
            except ValueError:
                flash("Enter a valid amount and discount percentage.", "danger")
                return redirect(url_for("new_invoice"))
            if not math.isfinite(total) or total <= 0 or not math.isfinite(discount_percentage) or not 0 <= discount_percentage <= 100:
                flash("Total must be positive and discount must be between 0 and 100 percent.", "danger")
                return redirect(url_for("new_invoice"))
            user = get_current_user()
            is_admin = bool(user.role and user.role.name == "Admin")
            needs_approval = discount_percentage > 31 and not is_admin
            request_note = request.form.get("discount_request_note", "").strip()
            if needs_approval and not request_note:
                flash("Add a reason when requesting a discount above 31%.", "danger")
                return redirect(url_for("new_invoice"))
            discount_amount = round(total * discount_percentage / 100, 2)
            invoice_number = request.form.get("invoice_number") or generate_invoice_number()
            invoice_date = parse_date(request.form.get("due_date")) or datetime.utcnow().date()
            invoice = Invoice(
                patient_id=patient.id,
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                service_type=request.form.get("service_type", "Consultation").strip() or "Consultation",
                total_amount=total,
                paid_amount=0,
                balance_amount=0 if needs_approval else round(total - discount_amount, 2),
                discount=discount_amount,
                discount_percentage=discount_percentage,
                discount_approval_status="Pending" if needs_approval else ("Approved" if discount_percentage > 31 else "Not Required"),
                discount_requested_by_id=user.id if discount_percentage > 31 else None,
                discount_reviewed_by_id=user.id if discount_percentage > 31 and is_admin else None,
                discount_requested_at=datetime.utcnow() if discount_percentage > 31 else None,
                discount_reviewed_at=datetime.utcnow() if discount_percentage > 31 and is_admin else None,
                discount_request_note=request_note if discount_percentage > 31 else None,
                tax=0,
                status="Pending Approval" if needs_approval else "Pending",
                notes=request.form.get("description").strip(),
            )
            db.session.add(invoice)
            db.session.commit()
            log_activity(session["user_id"], "Invoice created", f"Invoice {invoice.invoice_number} created for {patient.full_name}")
            if needs_approval:
                flash("Invoice saved as pending approval. It cannot be completed or paid until management approves the discount.", "warning")
            else:
                flash("Invoice created successfully.", "success")
            return redirect(url_for("billing"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template("invoice_form.html", patients=patients, invoice=None)

    @app.route("/billing/<int:invoice_id>/discount-review", methods=["POST"])
    @login_required
    @permission_required("billing_view")
    def review_invoice_discount(invoice_id):
        user = get_current_user()
        if not user.role or user.role.name != "Admin":
            abort(403)
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.discount_approval_status != "Pending":
            abort(409)
        action = request.form.get("action")
        if action == "approve":
            invoice.discount_approval_status = "Approved"
            invoice.status = "Pending"
            invoice.balance_amount = max(round(invoice.total_amount - invoice.discount, 2), 0)
            message = "Discount approved. The invoice is now available for billing completion."
            log_action = "Invoice discount approved"
        elif action == "reject":
            invoice.discount_approval_status = "Rejected"
            invoice.status = "Discount Rejected"
            invoice.balance_amount = 0
            message = "Discount request rejected. Billing staff can revise and resubmit the invoice."
            log_action = "Invoice discount rejected"
        else:
            abort(400)
        invoice.discount_reviewed_by_id = user.id
        invoice.discount_reviewed_at = datetime.utcnow()
        invoice.discount_review_note = request.form.get("review_note", "").strip()
        db.session.commit()
        log_activity(user.id, log_action, f"Invoice {invoice.invoice_number}: {invoice.discount_review_note or action}")
        flash(message, "success" if action == "approve" else "warning")
        return redirect(url_for("billing"))

    @app.route("/billing/<int:invoice_id>/complete", methods=["POST"])
    @login_required
    @permission_required("payment_add")
    def complete_invoice(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.discount_approval_status == "Pending" or invoice.status in (
            "Pending Approval",
            "Discount Rejected",
        ):
            abort(409)
        if invoice.discount_percentage > 31 and invoice.discount_approval_status != "Approved":
            abort(409)
        if invoice.balance_amount <= 0 or invoice.status == "Paid":
            abort(409)
        payment_method = request.form.get("payment_method", "")
        if payment_method not in ("Cash", "Card", "UPI", "Bank Transfer"):
            abort(400)
        payment = Payment(
            patient_id=invoice.patient_id,
            invoice_id=invoice.id,
            amount=invoice.balance_amount,
            payment_method=payment_method,
            payment_status="Completed",
            payment_date=datetime.utcnow().date(),
            notes=f"Completed invoice {invoice.invoice_number}",
        )
        invoice.paid_amount = invoice.total_amount - invoice.discount
        invoice.balance_amount = 0
        invoice.status = "Paid"
        db.session.add(payment)
        db.session.commit()
        log_activity(
            session["user_id"],
            "Invoice completed",
            f"Invoice {invoice.invoice_number} completed by {payment_method}",
        )
        flash("Invoice marked as paid.", "success")
        return redirect(url_for("billing"))

    @app.route("/billing/<int:invoice_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("billing_add")
    def edit_invoice(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        if invoice.paid_amount > 0 or invoice.status not in ("Pending", "Pending Approval", "Discount Rejected"):
            abort(403)
        if request.method == "POST":
            try:
                total = float(request.form.get("total_amount") or 0)
                discount_percentage = float(request.form.get("discount_percentage") or 0)
            except ValueError:
                flash("Enter a valid amount and discount percentage.", "danger")
                return redirect(url_for("edit_invoice", invoice_id=invoice.id))
            if not math.isfinite(total) or total <= 0 or not math.isfinite(discount_percentage) or not 0 <= discount_percentage <= 100:
                flash("Total must be positive and discount must be between 0 and 100 percent.", "danger")
                return redirect(url_for("edit_invoice", invoice_id=invoice.id))
            user = get_current_user()
            is_admin = bool(user.role and user.role.name == "Admin")
            needs_approval = discount_percentage > 31 and not is_admin
            request_note = request.form.get("discount_request_note", "").strip()
            if needs_approval and not request_note:
                flash("Add a reason when requesting a discount above 31%.", "danger")
                return redirect(url_for("edit_invoice", invoice_id=invoice.id))
            invoice.patient_id = Patient.query.get_or_404(request.form.get("patient_id")).id
            invoice.total_amount = total
            invoice.discount_percentage = discount_percentage
            invoice.discount = round(total * discount_percentage / 100, 2)
            invoice.balance_amount = 0 if needs_approval else round(total - invoice.discount, 2)
            invoice.discount_approval_status = "Pending" if needs_approval else ("Approved" if discount_percentage > 31 else "Not Required")
            invoice.discount_requested_by_id = user.id if discount_percentage > 31 else None
            invoice.discount_requested_at = datetime.utcnow() if discount_percentage > 31 else None
            invoice.discount_reviewed_by_id = user.id if discount_percentage > 31 and is_admin else None
            invoice.discount_reviewed_at = datetime.utcnow() if discount_percentage > 31 and is_admin else None
            invoice.discount_request_note = request_note if discount_percentage > 31 else None
            invoice.discount_review_note = None
            invoice.invoice_date = parse_date(request.form.get("due_date")) or invoice.invoice_date
            invoice.notes = request.form.get("description", "").strip()
            invoice.status = "Pending Approval" if needs_approval else "Pending"
            db.session.commit()
            log_activity(user.id, "Invoice revised", f"Invoice {invoice.invoice_number} revised")
            flash("Invoice revised and submitted for approval." if needs_approval else "Invoice updated.", "warning" if needs_approval else "success")
            return redirect(url_for("billing"))
        patients = Patient.query.order_by(Patient.full_name.asc()).all()
        return render_template("invoice_form.html", patients=patients, invoice=invoice)

    @app.route("/payments")
    @login_required
    @permission_required("payment_view")
    def payments():
        payment_list = Payment.query.order_by(Payment.payment_date.desc()).all()
        return render_template("payments.html", payments=payment_list)

    @app.route("/invoices/<int:invoice_id>")
    @login_required
    @permission_required("billing_view")
    def invoice_detail(invoice_id):
        invoice = Invoice.query.get_or_404(invoice_id)
        return render_template("billing.html", invoices=[invoice], total_revenue=invoice.total_amount, pending=invoice.balance_amount)

    @app.route("/staff")
    @login_required
    @permission_required("staff_management")
    def staff_list():
        users = User.query.order_by(User.created_at.desc()).all()
        roles = Role.query.order_by(Role.name.asc()).all()
        permissions = Permission.query.order_by(Permission.name.asc()).all()
        return render_template("staff.html", staff=users, roles=roles, permissions=permissions)

    @app.route("/staff/new", methods=["GET", "POST"])
    @login_required
    @permission_required("staff_management")
    def create_staff():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return redirect(url_for("create_staff"))
            role_id = int(request.form.get("role_id"))
            role = Role.query.get_or_404(role_id)
            user = User(
                username=username,
                password_hash=generate_password_hash(request.form.get("password")),
                full_name=request.form.get("full_name").strip(),
                role_id=role.id,
                is_active=True,
            )
            db.session.add(user)
            db.session.commit()
            for permission_id in request.form.getlist("permission_ids"):
                permission = Permission.query.get(int(permission_id))
                if permission:
                    user.permissions.append(permission)
            db.session.commit()
            log_activity(session["user_id"], "Staff created", f"Created staff member {user.full_name}")
            flash("Staff record created successfully.", "success")
            return redirect(url_for("staff_list"))
        roles = Role.query.order_by(Role.name.asc()).all()
        permissions = Permission.query.order_by(Permission.name.asc()).all()
        return render_template("staff_form.html", roles=roles, permissions=permissions, staff_user=None, form_title="Add Staff")

    @app.route("/staff/add", methods=["GET", "POST"])
    @login_required
    @permission_required("staff_management")
    def new_staff():
        return create_staff()

    @app.route("/staff/<int:user_id>/edit", methods=["GET", "POST"])
    @login_required
    @permission_required("staff_management")
    def edit_staff(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == "POST":
            user.full_name = request.form.get("full_name").strip()
            user.username = request.form.get("username").strip()
            if request.form.get("password"):
                user.password_hash = generate_password_hash(request.form.get("password"))
            user.department = request.form.get("department", "").strip() if hasattr(user, "department") else user.department
            role = Role.query.get_or_404(int(request.form.get("role_id")))
            user.role_id = role.id
            db.session.commit()
            log_activity(session["user_id"], "Staff updated", f"Updated staff record for {user.full_name}")
            flash("Staff record updated.", "success")
            return redirect(url_for("staff_list"))
        roles = Role.query.order_by(Role.name.asc()).all()
        return render_template("staff_form.html", staff_user=user, roles=roles, form_title="Edit Staff")

    @app.route("/staff/<int:user_id>/permissions", methods=["GET", "POST"])
    @login_required
    @permission_required("staff_management")
    def edit_staff_permissions(user_id):
        user = User.query.get_or_404(user_id)
        if user.username == "admin":
            flash("Admin permissions cannot be modified.", "danger")
            return redirect(url_for("staff_list"))
        if request.method == "POST":
            user.permissions = []
            for permission_id in request.form.getlist("permission_ids"):
                permission = Permission.query.get(int(permission_id))
                if permission:
                    user.permissions.append(permission)
            db.session.commit()
            log_activity(session["user_id"], "Permissions updated", f"Updated permissions for {user.full_name}")
            flash("Permissions updated successfully.", "success")
            return redirect(url_for("staff_list"))
        permissions = Permission.query.order_by(Permission.name.asc()).all()
        user_permission_ids = {p.id for p in user.permissions}
        return render_template("staff_permissions.html", user=user, permissions=permissions, user_permission_ids=user_permission_ids)

    @app.route("/reports")
    @login_required
    @permission_required("reports_view")
    def reports():
        report_data = {
            "patient_count": Patient.query.count(),
            "appointment_count": Appointment.query.count(),
            "revenue": db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).scalar() or 0,
            "paid_invoices": Invoice.query.filter(Invoice.status == "Paid").count(),
        }
        return render_template("reports.html", report_data=report_data)

    @app.route("/audit-logs")
    @login_required
    @permission_required("staff_management")
    def audit_logs():
        logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
        return render_template("audit_logs.html", logs=logs)

    @app.route("/backup")
    @login_required
    @permission_required("reports_export")
    def backup_database():
        backup_dir = BASE_DIR / "backups"
        backup_dir.mkdir(exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"ree_forma_backup_{timestamp}.sql"
        database_path = BASE_DIR / "ree_forma.db"
        if database_path.exists():
            connection = sqlite3.connect(str(database_path))
            with sqlite3.connect(str(backup_path)) as backup_conn:
                connection.backup(backup_conn)
            connection.close()
            flash("Database backup created successfully.", "success")
            return send_file(backup_path, mimetype="application/sql", as_attachment=True, download_name=backup_path.name)
        flash("No database file exists yet.", "warning")
        return redirect(url_for("dashboard"))

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok", "services": ["api", "frontend"]})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
