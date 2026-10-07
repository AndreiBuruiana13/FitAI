from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, create_engine, Index
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime
import os

                       
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitai_professional.db")

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db(database_url: str = None):
    global engine, SessionLocal
    target_url = database_url or SQLALCHEMY_DATABASE_URL
    if target_url.startswith("sqlite:///:memory:"):
        engine = create_engine(
            target_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(target_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

                             
                       
                             

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    weight_kg = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    devices = relationship(
        "Device",
        back_populates="owner",
        cascade="all, delete-orphan"
    )
    sessions = relationship(
        "WorkoutSession",
        back_populates="user",
        cascade="all, delete-orphan"
    )

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    mac_address = Column(String, unique=True, index=True)
    device_type = Column(String)

    owner = relationship("User", back_populates="devices")

class WorkoutSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    activity_type = Column(String, nullable=True) 
    avg_heart_rate = Column(Float, nullable=True)
    max_speed = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    telemetry = relationship(
        "TelemetryData",
        back_populates="session",
        cascade="all, delete-orphan"
    )

class TelemetryData(Base):
    __tablename__ = "telemetry_data"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    speed_mps = Column(Float, nullable=False)
    heart_bpm = Column(Integer, nullable=True)
    accel_rms = Column(Float, nullable=True)
    accel_variance = Column(Float, nullable=True)
    accel_magnitude_mean = Column(Float, nullable=True)
    gyro_rms = Column(Float, nullable=True)
    mcr = Column(Integer, nullable=True)
    iqr = Column(Float, nullable=True)
    spo2 = Column(Float, nullable=True)
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    label = Column(String, nullable=True, default="UNKNOWN")

    session = relationship("WorkoutSession", back_populates="telemetry")

                             
                                 
                             

class DailyRecovery(Base):
    """
    Central Nervous System (CNS) Recovery & Readiness Tracking.
    
    Stores daily recovery metrics to forecast athlete readiness.
    Academic Rationale:
    - Sleep Hours (30%): CNS restoration occurs primarily during NREM sleep stages
    - Resting Heart Rate (25%): Decreased RHR indicates parasympathetic activation (recovery)
    - Muscle Soreness (35%): DOMS (Delayed Onset Muscle Soreness) is key NREM biomarker
    - 7-Day Moving Average (10%): Captures chronic fatigue trends
    
    Readiness Score = weighted mean of normalized components × 100
    """
    __tablename__ = "daily_recovery"
    
                                                                   
    __table_args__ = (Index('ix_recovery_user_date', 'user_id', 'date'),)
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String, nullable=False, index=True)                          
    
                      
    sleep_hours = Column(Float, nullable=True)                   
    resting_heart_rate = Column(Integer, nullable=True)                                     
    muscle_soreness = Column(Float, nullable=True)                                          
    
                                
    readiness_score = Column(Float, nullable=True)         
    
              
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")