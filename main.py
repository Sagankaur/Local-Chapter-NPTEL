# =========================
# file: app.py
# =========================
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

import io
import csv
import os
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lc.db' 
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@localhost:3306/lcdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ----------------------
# Model
# ----------------------
class LCActivity(db.Model):
    __tablename__ = 'lc_activity'
    id = db.Column(db.Integer, primary_key=True)
    lc_id = db.Column(db.String, nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    enrollments = db.Column(db.Integer, default=0, nullable=False)
    registrations = db.Column(db.Integer, default=0, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('lc_id', 'year', name='uq_lc_year'),
    )

# ----------------------
# Helpers
# ----------------------

def latest_year():
    return db.session.query(func.max(LCActivity.year)).scalar()


def active_condition(model_alias=None):
    m = model_alias or LCActivity
    return or_(m.enrollments > 0, m.registrations > 0)


def get_active_in_year(y):
    return (
        db.session.query(LCActivity.lc_id)
        .filter(LCActivity.year == y, active_condition())
        .distinct()
    )


def get_inactive_set_for_latest():
    y = latest_year()
    if y is None:
        return set(), None
    past_active = (
        db.session.query(LCActivity.lc_id)
        .filter(LCActivity.year < y, active_condition())
        .distinct()
    )
    latest_active = get_active_in_year(y)
    past_set = {row[0] for row in past_active}
    latest_set = {row[0] for row in latest_active}
    return (past_set - latest_set), y


def trend_active_inactive():
    years = [row[0] for row in db.session.query(LCActivity.year).distinct().all()]
    years = sorted(years)
    data = []
    for y in years:
        active_cnt = (
            db.session.query(LCActivity.lc_id)
            .filter(LCActivity.year == y, active_condition())
            .distinct()
            .count()
        )
        total_lcs = (
            db.session.query(LCActivity.lc_id)
            .filter(LCActivity.year == y)
            .distinct()
            .count()
        )
        inactive_cnt = max(total_lcs - active_cnt, 0)
        data.append({'year': y, 'active': active_cnt, 'inactive': inactive_cnt})
    return data

# ----------------------
# Pages
# ----------------------

@app.route('/')
def index():
    y = latest_year()
    active_now = 0
    if y is not None:
        active_now = get_active_in_year(y).count()
    inactive_set, _ = get_inactive_set_for_latest()

    trend = trend_active_inactive()

    # search
    lc_id = request.args.get('lc_id')
    lc_timeline = []
    if lc_id:
        records = (
            LCActivity.query
            .filter(LCActivity.lc_id == lc_id)
            .order_by(LCActivity.year.asc())
            .all()
        )
        lc_timeline = [
            {
                'year': r.year,
                'enrollments': r.enrollments,
                'registrations': r.registrations,
                'active': (r.enrollments > 0 or r.registrations > 0)
            }
            for r in records
        ]

    return render_template(
        'index.html',
        latest_year=y,
        active_now=active_now,
        inactive_count=len(inactive_set),
        inactive_list=sorted(list(inactive_set)),
        trend_json=json.dumps(trend),
        lc_id=lc_id or '',
        lc_timeline_json=json.dumps(lc_timeline),
    )

# ----------------------
# APIs
# ----------------------

@app.route('/api/active_lcs')
def api_active_lcs():
    y = latest_year()
    if y is None:
        return jsonify({'latest_year': None, 'active_count': 0, 'active_lcs': []})
    active = [row[0] for row in get_active_in_year(y).all()]
    return jsonify({'latest_year': y, 'active_count': len(active), 'active_lcs': active})


@app.route('/api/inactive_lcs')
def api_inactive_lcs():
    inactive_set, y = get_inactive_set_for_latest()
    return jsonify({'latest_year': y, 'inactive_count': len(inactive_set), 'inactive_lcs': sorted(list(inactive_set))})


@app.route('/api/trend')
def api_trend():
    return jsonify(trend_active_inactive())


@app.route('/api/lc/<lc_id>')
def api_lc(lc_id):
    recs = (
        LCActivity.query
        .filter(LCActivity.lc_id == lc_id)
        .order_by(LCActivity.year.asc())
        .all()
    )
    return jsonify([
        {
            'year': r.year,
            'enrollments': r.enrollments,
            'registrations': r.registrations,
            'active': (r.enrollments > 0 or r.registrations > 0)
        }
        for r in recs
    ])


@app.route('/export_inactive')
def export_inactive():
    inactive_set, y = get_inactive_set_for_latest()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['inactive_lc_id', 'note'])
    for lc in sorted(list(inactive_set)):
        writer.writerow([lc, f'inactive in latest_year={y}'])
    mem = io.BytesIO(output.getvalue().encode('utf-8'))
    mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='inactive_lcs.csv')

# ----------------------
# Data ingestion
# ----------------------

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            flash('No file provided', 'danger')
            return redirect(url_for('upload'))
        filename = secure_filename(f.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        f.save(path)

        # Expect columns: lc_id, year, enrollments, registrations
        with open(path, 'r', newline='', encoding='utf-8') as fh:
            rdr = csv.DictReader(fh)
            rows = list(rdr)
        # Basic validation
        required = {'lc_id', 'year', 'enrollments', 'registrations'}
        if not required.issubset(set([c.strip() for c in rdr.fieldnames])):
            flash('CSV missing required columns', 'danger')
            return redirect(url_for('upload'))

        inserted = 0
        for row in rows:
            try:
                rec = LCActivity(
                    lc_id=str(row['lc_id']).strip(),
                    year=int(row['year']),
                    enrollments=int(row['enrollments']),
                    registrations=int(row['registrations']),
                )
                # upsert semantics: if exists, update
                existing = (
                    LCActivity.query
                    .filter_by(lc_id=rec.lc_id, year=rec.year)
                    .one_or_none()
                )
                if existing:
                    existing.enrollments = rec.enrollments
                    existing.registrations = rec.registrations
                else:
                    db.session.add(rec)
                inserted += 1
            except Exception as e:
                db.session.rollback()
                flash(f'Row skipped due to error: {e}', 'warning')
        db.session.commit()
        flash(f'Ingested/updated {inserted} rows', 'success')
        return redirect(url_for('index'))

    return render_template('upload.html')

# ----------------------
# CLI helpers
# ----------------------

@app.cli.command('init-db')
def init_db():
    """Initialize the database tables."""
    db.create_all()
    print('Database initialized.')


@app.cli.command('seed')
def seed():
    """Seed sample data for quick demo."""
    db.create_all()
    db.session.query(LCActivity).delete()
    sample = [
        # lc_id, year, enrollments, registrations
        ('LC001', 2021, 30, 12),
        ('LC001', 2022, 10, 5),
        ('LC001', 2023, 0, 0),
        ('LC001', 2024, 0, 0),
        ('LC002', 2022, 5, 7),
        ('LC002', 2023, 3, 4),
        ('LC002', 2024, 2, 0),
        ('LC003', 2021, 0, 10),
        ('LC003', 2022, 0, 0),
        ('LC003', 2023, 0, 0),
        ('LC004', 2023, 8, 2),
        ('LC004', 2024, 0, 0),
        ('LC005', 2022, 1, 1),
        ('LC005', 2023, 2, 0),
        ('LC005', 2024, 0, 0),
        ('LC006', 2024, 9, 3),
    ]
    for lc, y, e, r in sample:
        db.session.add(LCActivity(lc_id=lc, year=y, enrollments=e, registrations=r))
    db.session.commit()
    print('Seeded sample data.')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

