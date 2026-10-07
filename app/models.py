               
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import List, Optional
from datetime import date, datetime

class TelemetrySample(BaseModel):
    model_config = ConfigDict(extra='ignore')

    timestamp: Optional[datetime] = Field(None)
    speed_mps: float = Field(ge=0)
                                                                                 
    heart_bpm: Optional[float] = None
    accel_rms: Optional[float] = Field(None, ge=0)
    accel_variance: Optional[float] = None
    accel_magnitude_mean: Optional[float] = None
    gyro_rms: Optional[float] = None
    mcr: Optional[int] = None
    iqr: Optional[float] = None
    spo2: Optional[float] = None
    gps_lat: Optional[float] = Field(None, ge=-90, le=90)
    gps_lon: Optional[float] = Field(None, ge=-180, le=180)
    label: str = Field("UNKNOWN", max_length=32)

class IngestResponse(BaseModel):
    inserted: int
    session_id: int
    activity_type: str
    message: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, description="Password must be at least 8 characters")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


                             
                                 
                             

class DailyRecoveryData(BaseModel):
    """Request model for logging daily recovery metrics."""
    date: date                                                     
    sleep_hours: Optional[float] = Field(None, ge=0, le=24, description="Sleep hours: 0-24")
    resting_heart_rate: Optional[int] = Field(None, ge=30, le=220, description="RHR in bpm: 30-220")
    muscle_soreness: Optional[float] = Field(None, ge=0, le=10, description="Soreness scale: 0-10")

class DailyRecoveryResponse(BaseModel):
    """Response model for recovery data with calculated readiness score."""
    id: int
    date: str
    sleep_hours: Optional[float]
    resting_heart_rate: Optional[int]
    muscle_soreness: Optional[float]
    readiness_score: Optional[float]
    
    model_config = ConfigDict(from_attributes=True)

class RecoveryTrendResponse(BaseModel):
    """Response model for 30-day recovery trend."""
    dates: List[str]
    readiness_scores: List[float]
    sleep_hours_list: List[Optional[float]]
    resting_hr_list: List[Optional[int]]
    soreness_list: List[Optional[float]]
    average_readiness: float
    trend: str                                      
    trend_slope: Optional[float] = None


                             
                                 
                             

class ForecastDay(BaseModel):
    date: str
    predicted_score: float
    recommendation: str

class RecoveryForecastResponse(BaseModel):
    forecast: List[ForecastDay]
    trend_direction: str
    slope_per_day: float
    message: str