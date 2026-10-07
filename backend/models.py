from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)

user_permissions = db.Table(
    "user_permissions",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)


class Permission(db.Model):
    __tablename__ = "permissions"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    roles = db.relationship("Role", secondary=role_permissions, back_populates="permissions")
    users = db.relationship("User", secondary=user_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.name}>"


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)

    users = db.relationship("User", back_populates="role")
    permissions = db.relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    department = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role = db.relationship("Role", back_populates="users")
    permissions = db.relationship("Permission", secondary=user_permissions, back_populates="users")

    def has_permission(self, permission_name):
        if self.role and self.role.name == "Admin":
            return True
        permission_names = {perm.name for perm in self.permissions}
        role_permission_names = {perm.name for perm in self.role.permissions} if self.role else set()
        return permission_name in permission_names or permission_name in role_permission_names

    def __repr__(self):
        return f"<User {self.username}>"


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    dob = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    occupation = db.Column(db.String(120), nullable=True)
    referral_source = db.Column(db.String(120), nullable=True)
    purpose_of_visit = db.Column(db.Text, nullable=True)
    concern = db.Column(db.Text, nullable=True)
    current_height = db.Column(db.String(40), nullable=True)
    current_weight = db.Column(db.String(40), nullable=True)
    signature = db.Column(db.String(150), nullable=True)
    emergency_contact = db.Column(db.String(150), nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    existing_conditions = db.Column(db.Text, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    referring_doctor = db.Column(db.String(120), nullable=True)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    appointments = db.relationship("Appointment", back_populates="patient")
    assessments = db.relationship("Assessment", back_populates="patient")
    treatments = db.relationship("TreatmentRecord", back_populates="patient")
    invoices = db.relationship("Invoice", back_populates="patient")
    patient_packages = db.relationship("PatientPackage", back_populates="patient")
    payments = db.relationship("Payment", back_populates="patient")


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    patient_name = db.Column(db.String(150), nullable=False)
    physiotherapist_name = db.Column(db.String(150), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False)
    appointment_time = db.Column(db.String(20), nullable=False)
    appointment_end_time = db.Column(db.String(20), nullable=True)
    appointment_category = db.Column(db.String(80), nullable=False, default="Physiotherapy")
    appointment_type = db.Column(db.String(80), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), default="Scheduled")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="appointments")


class CompanySchedule(db.Model):
    __tablename__ = "company_schedules"

    id = db.Column(db.Integer, primary_key=True)
    default_start_time = db.Column(db.String(5), nullable=False, default="09:00")
    default_end_time = db.Column(db.String(5), nullable=False, default="17:00")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StaffSchedule(db.Model):
    __tablename__ = "staff_schedules"

    id = db.Column(db.Integer, primary_key=True)
    staff_name = db.Column(db.String(150), nullable=False)
    work_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)
    uses_company_default = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("staff_name", "work_date", name="uq_staff_schedule_day"),
    )


class Assessment(db.Model):
    __tablename__ = "assessments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    patient_name = db.Column(db.String(150), nullable=False)
    assessment_age = db.Column(db.Integer, nullable=True)
    assessment_gender = db.Column(db.String(20), nullable=True)
    assessment_type = db.Column(db.String(80), default="Physiotherapy Assessment", nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    chief_complaint = db.Column(db.Text, nullable=True)
    present_history = db.Column(db.Text, nullable=True)
    past_medical_history = db.Column(db.Text, nullable=True)
    surgical_history = db.Column(db.Text, nullable=True)
    medication = db.Column(db.Text, nullable=True)
    pain_location = db.Column(db.Text, nullable=True)
    symptom_onset = db.Column(db.String(80), nullable=True)
    pain_intensity = db.Column(db.String(50), nullable=True)
    pain_duration = db.Column(db.String(50), nullable=True)
    pain_type = db.Column(db.String(50), nullable=True)
    aggravating_factors = db.Column(db.Text, nullable=True)
    relieving_factors = db.Column(db.Text, nullable=True)
    gcs_score = db.Column(db.Integer, nullable=True)
    superficial_sensation = db.Column(db.String(80), nullable=True)
    deep_sensation = db.Column(db.String(80), nullable=True)
    reflex_right_upper_limb = db.Column(db.String(80), nullable=True)
    reflex_right_lower_limb = db.Column(db.String(80), nullable=True)
    reflex_left_upper_limb = db.Column(db.String(80), nullable=True)
    reflex_left_lower_limb = db.Column(db.String(80), nullable=True)
    reflex_muscles_examined = db.Column(db.Text, nullable=True)
    posture_assessment = db.Column(db.Text, nullable=True)
    range_of_motion = db.Column(db.Text, nullable=True)
    muscle_strength = db.Column(db.Text, nullable=True)
    muscle_strength_mmt = db.Column(db.String(80), nullable=True)
    tenderness = db.Column(db.Text, nullable=True)
    palpation = db.Column(db.Text, nullable=True)
    posture = db.Column(db.Text, nullable=True)
    investigation = db.Column(db.Text, nullable=True)
    problem_list = db.Column(db.Text, nullable=True)
    goal = db.Column(db.Text, nullable=True)
    flexibility = db.Column(db.Text, nullable=True)
    balance = db.Column(db.Text, nullable=True)
    gait_assessment = db.Column(db.Text, nullable=True)
    functional_assessment = db.Column(db.Text, nullable=True)
    neurological_assessment = db.Column(db.Text, nullable=True)
    special_tests = db.Column(db.Text, nullable=True)
    clinical_findings = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    treatment_goals = db.Column(db.Text, nullable=True)
    short_term_goals = db.Column(db.Text, nullable=True)
    long_term_goals = db.Column(db.Text, nullable=True)
    treatment_plan = db.Column(db.Text, nullable=True)
    treatment_plan_entries = db.Column(db.Text, nullable=True)
    physiotherapist_notes = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    follow_up_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="assessments")


class TreatmentRecord(db.Model):
    __tablename__ = "treatment_records"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    patient_name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)
    physiotherapist_name = db.Column(db.String(150), nullable=False)
    treatment_type = db.Column(db.String(120), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    patient_response = db.Column(db.Text, nullable=True)
    next_plan = db.Column(db.Text, nullable=True)
    treatment_performed = db.Column(db.Text, nullable=True)
    exercises = db.Column(db.Text, nullable=True)
    therapy_techniques = db.Column(db.Text, nullable=True)
    pain_before = db.Column(db.String(30), nullable=True)
    pain_after = db.Column(db.String(30), nullable=True)
    progress = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    next_appointment = db.Column(db.Date, nullable=True)
    follow_up_instructions = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="treatments")


class ServicePackage(db.Model):
    __tablename__ = "packages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    session_count = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, default=0.0)
    validity_days = db.Column(db.Integer, default=30)
    included_services = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient_packages = db.relationship("PatientPackage", back_populates="package")

    @property
    def active_status(self):
        return "Active" if self.is_active else "Inactive"


class PatientPackage(db.Model):
    __tablename__ = "patient_packages"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey("packages.id"), nullable=False)
    start_date = db.Column(db.Date, default=datetime.utcnow().date())
    expiry_date = db.Column(db.Date, nullable=True)
    total_sessions = db.Column(db.Integer, default=0)
    used_sessions = db.Column(db.Integer, default=0)
    remaining_sessions = db.Column(db.Integer, default=0)
    payment_status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="patient_packages")
    package = db.relationship("ServicePackage", back_populates="patient_packages")


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_date = db.Column(db.Date, default=datetime.utcnow().date())
    service_type = db.Column(db.String(80), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    paid_amount = db.Column(db.Float, default=0.0)
    balance_amount = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    discount_percentage = db.Column(db.Float, nullable=False, default=0.0)
    discount_approval_status = db.Column(db.String(30), nullable=False, default="Not Required")
    discount_requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    discount_reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    discount_requested_at = db.Column(db.DateTime, nullable=True)
    discount_reviewed_at = db.Column(db.DateTime, nullable=True)
    discount_request_note = db.Column(db.Text, nullable=True)
    discount_review_note = db.Column(db.Text, nullable=True)
    tax = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(30), default="Pending")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="invoices")
    payments = db.relationship("Payment", back_populates="invoice")
    discount_requested_by = db.relationship("User", foreign_keys=[discount_requested_by_id])
    discount_reviewed_by = db.relationship("User", foreign_keys=[discount_reviewed_by_id])

    @property
    def patient_name(self):
        return self.patient.full_name if self.patient else ""

    @property
    def due_date(self):
        return self.invoice_date


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=True)
    amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(30), default="Pending")
    payment_date = db.Column(db.Date, default=datetime.utcnow().date())
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    patient = db.relationship("Patient", back_populates="payments")
    invoice = db.relationship("Invoice", back_populates="payments")

    @property
    def patient_name(self):
        return self.patient.full_name if self.patient else ""

    @property
    def invoice_number(self):
        return self.invoice.invoice_number if self.invoice else ""


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default="system")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User")
