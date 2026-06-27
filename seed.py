"""
Database seeder -- populates demo data for development and testing.
Run: python seed.py
"""
import random
from datetime import datetime, timedelta, timezone
import os
from app import create_app
from models import db, User, CrimeCategory, CrimeReport, Alert, Notification

app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

# Crime categories
CATEGORIES = [
    ('Robbery', 'robbery', 'Theft using force or threat of force'),
    ('Assault', 'assault', 'Physical attack on a person'),
    ('Burglary', 'burglary', 'Unlawful entry into a building to commit theft'),
    ('Fraud', 'fraud', 'Deception for financial or personal gain'),
    ('Vandalism', 'vandalism', 'Deliberate destruction of property'),
    ('Kidnapping', 'kidnapping', 'Unlawful abduction of a person'),
    ('Drug Offense', 'drugs', 'Possession, distribution, or manufacturing of illegal substances'),
    ('Cybercrime', 'cybercrime', 'Criminal activity carried out using computers or the internet'),
    ('Domestic Violence', 'domestic', 'Violence or abuse within a domestic setting'),
    ('Murder', 'murder', 'Unlawful killing of a person'),
    ('Arson', 'arson', 'Deliberate setting of fire to property'),
    ('Other', 'other', 'Other criminal activities not listed above'),
]

# Demo users (username, email, password, full_name, role, phone, latitude, longitude)
USERS = [
    ('admin', 'admin@crimealert.ng', 'Admin@123', 'System Administrator', 'admin', '08012345670', None, None),
    ('officer_john', 'john.officer@police.ng', 'Officer@123', 'John Adeyemi', 'officer', '08012345671', None, None),
    ('officer_grace', 'grace.officer@police.ng', 'Officer@123', 'Grace Okonkwo', 'officer', '08012345672', None, None),
    ('citizen_mike', 'mike@gmail.com', 'Citizen@123', 'Michael Eze', 'citizen', '08012345673', 6.6018, 3.3515),   # Ikeja
    ('citizen_ada', 'ada@gmail.com', 'Citizen@123', 'Adaeze Nwosu', 'citizen', '08012345674', 6.4474, 3.4737),    # Lekki
    ('citizen_emeka', 'emeka@gmail.com', 'Citizen@123', 'Emeka Obi', 'citizen', '08012345675', 6.5244, 3.3792),   # Yaba
]

# Sample reports (title, description, category_index, severity, status, lat, lng, address)
REPORTS = [
    ('Armed Robbery at Ikeja Market', 'A group of armed men attacked shoppers at Ikeja main market around 3pm. They were armed with machetes and collected valuables from at least 10 people.', 0, 'critical', 'investigating', 6.6018, 3.3515, 'Ikeja Market, Lagos'),
    ('Phone Snatching on Third Mainland Bridge', 'My phone was snatched by a motorcyclist while I was in traffic on Third Mainland Bridge.', 0, 'medium', 'pending', 6.4698, 3.3895, 'Third Mainland Bridge, Lagos'),
    ('Assault at Leisure Mall', 'Was physically attacked by an unknown person at the parking lot of Leisure Mall Surulere.', 1, 'high', 'investigating', 6.4969, 3.3574, 'Leisure Mall, Surulere, Lagos'),
    ('House Break-in at Lekki Phase 1', 'My house was broken into while I was at work. Laptops, jewelry and cash were stolen.', 2, 'high', 'resolved', 6.4474, 3.4737, 'Lekki Phase 1, Lagos'),
    ('Online Banking Fraud', 'Received a phishing email and unknowingly provided my banking details. N500,000 was withdrawn.', 3, 'critical', 'investigating', 6.4550, 3.3841, 'Victoria Island, Lagos'),
    ('Car Vandalism at Ajah', 'My car was vandalized overnight. Windows smashed and side mirrors broken.', 4, 'medium', 'pending', 6.4698, 3.5852, 'Ajah, Lagos'),
    ('Suspected Drug Dealing at Oshodi', 'There is suspicious activity at the abandoned building near Oshodi bus stop. People coming and going at odd hours.', 6, 'medium', 'pending', 6.5244, 3.3461, 'Oshodi, Lagos'),
    ('Cyberbullying Threats', 'I have been receiving death threats via social media from an anonymous account for the past week.', 7, 'high', 'investigating', 6.5244, 3.3792, 'Yaba, Lagos'),
    ('Domestic Violence Report', 'My neighbor is being physically abused by her partner. We can hear screaming every night.', 8, 'critical', 'investigating', 6.4300, 3.4200, 'Ikoyi, Lagos'),
    ('Vandalism of Public Property', 'Street lights on Admiralty Way have been deliberately destroyed.', 4, 'low', 'resolved', 6.4474, 3.4527, 'Admiralty Way, Lekki, Lagos'),
    ('Attempted Kidnapping', 'A suspicious van tried to force a woman into it near the school gate at 2pm.', 5, 'critical', 'investigating', 6.5955, 3.3464, 'Agege, Lagos'),
    ('Petty Theft at Bus Stop', 'My wallet was pickpocketed at CMS bus stop.', 0, 'low', 'dismissed', 6.4541, 3.4082, 'CMS Bus Stop, Lagos'),
    ('Fire Outbreak Suspected Arson', 'A shop in Balogun market caught fire under suspicious circumstances.', 10, 'critical', 'investigating', 6.4531, 3.3932, 'Balogun Market, Lagos Island'),
    ('Suspicious Package Found', 'A suspicious unattended package was found near the ATM at Gbagada.', 11, 'high', 'pending', 6.5524, 3.3831, 'Gbagada, Lagos'),
    ('Street Robbery at Night', 'Was robbed at gunpoint while walking home from work around 9pm.', 0, 'critical', 'pending', 6.5838, 3.3515, 'Ogba, Lagos'),
]


def seed():
    """Seed the database with demo data."""
    with app.app_context():
        print("Clearing existing data...")
        db.drop_all()
        db.create_all()

        # Seed categories
        print("Seeding crime categories...")
        cats = []
        for name, icon, desc in CATEGORIES:
            cat = CrimeCategory(name=name, icon=icon, description=desc)
            db.session.add(cat)
            cats.append(cat)
        db.session.commit()

        # Seed users
        print("Seeding users...")
        users = []
        colors = ['#00d4ff', '#8b5cf6', '#f97316', '#10b981', '#ef4444', '#f59e0b']
        for i, (uname, email, pw, name, role, phone, lat, lng) in enumerate(USERS):
            user = User(username=uname, email=email, full_name=name,
                        phone=phone, role=role, avatar_color=colors[i % len(colors)],
                        latitude=lat, longitude=lng)
            user.set_password(pw)
            db.session.add(user)
            users.append(user)
        db.session.commit()

        # Seed reports
        print("Seeding crime reports...")
        citizens = [u for u in users if u.role == 'citizen']
        officers = [u for u in users if u.role == 'officer']
        for i, (title, desc, cat_idx, sev, status, lat, lng, addr) in enumerate(REPORTS):
            reporter = citizens[i % len(citizens)]
            officer = officers[i % len(officers)] if status == 'investigating' else None
            days_ago = random.randint(1, 30)
            report = CrimeReport(
                title=title, description=desc, category_id=cats[cat_idx].id,
                severity=sev, status=status,
                latitude=lat, longitude=lng, address=addr,
                reporter_id=reporter.id,
                assigned_officer_id=officer.id if officer else None,
                created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            )
            db.session.add(report)
        db.session.commit()

        # Seed alerts
        print("Seeding alerts...")
        alert_data = [
            ('Armed Robbery Alert - Ikeja', 'Multiple armed robbery incidents reported around Ikeja. Please stay indoors after dark and report any suspicious activity.', 'critical', 6.6018, 3.3515),
            ('Traffic Diversion - Lekki', 'Due to ongoing police investigation, avoid Admiralty Way between 6pm and 6am.', 'medium', 6.4474, 3.4527),
            ('Missing Person - Victoria Island', 'A 12-year-old girl has been reported missing near Victoria Island. Please contact police if you have any information.', 'high', 6.4550, 3.3841),
        ]
        for title, msg, sev, lat, lng in alert_data:
            alert = Alert(title=title, message=msg, severity=sev,
                          area_latitude=lat, area_longitude=lng, area_radius=5.0,
                          created_by=officers[0].id, is_active=True)
            db.session.add(alert)
        db.session.commit()

        # Seed notifications
        print("Seeding notifications...")
        alerts = Alert.query.all()
        for citizen in citizens:
            for alert in alerts:
                notif = Notification(user_id=citizen.id, alert_id=alert.id,
                                     message=f"ALERT - {alert.title}: {alert.message}")
                db.session.add(notif)
        db.session.commit()

        print("\nDatabase seeded successfully!")
        print(f"   Categories: {len(CATEGORIES)}")
        print(f"   Users: {len(USERS)}")
        print(f"   Reports: {len(REPORTS)}")
        print(f"   Alerts: {len(alert_data)}")
        print("\nDemo Login Credentials:")
        print("   Admin:   admin / Admin@123")
        print("   Officer: officer_john / Officer@123")
        print("   Citizen: citizen_mike / Citizen@123")


if __name__ == '__main__':
    seed()
