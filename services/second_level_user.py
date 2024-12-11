from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import User, Channel, CompanyReport, CompanyInfo, ReportTransaction

async def get_dashboard_data(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Get dashboard data for a second-level user including their company reports,
    channel information, and statistics.
    """
    # Get user with their channel
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")

    # Get channel information
    channel = db.query(Channel).filter(Channel.id == user.channel_id).first()
    if not channel:
        raise ValueError("Channel not found")

    # Get user's company reports with company info
    company_reports = (
        db.query(CompanyReport)
        .join(CompanyInfo)
        .filter(CompanyReport.processed_by_user_id == user_id)
        .order_by(CompanyReport.created_at.desc())
        .all()
    )

    # Get user's statistics
    stats = {
        "total_uploads": (
            db.query(func.count(ReportTransaction.id))
            .filter(
                ReportTransaction.user_id == user_id,
                ReportTransaction.transaction_type == "UPLOAD"
            )
            .scalar()
        ),
        "total_downloads": (
            db.query(func.count(ReportTransaction.id))
            .filter(
                ReportTransaction.user_id == user_id,
                ReportTransaction.transaction_type == "DOWNLOAD"
            )
            .scalar()
        ),
        "total_reports": len(company_reports)
    }

    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "firstname": user.firstname,
            "lastname": user.lastname
        },
        "channel": {
            "id": channel.id,
            "channel_number": channel.channel_number,
            "channel_name": channel.channel_name,
            "channel_location": channel.channel_location,
            "industry": channel.industry,
            "contact_person": channel.contact_person,
            "contact_number": channel.contact_number,
            "registration_time": channel.registration_time
        },
        "stats": stats,
        "company_reports": [{
            "id": report.id,
            "created_at": report.created_at,
            "report_type": report.report_type,
            "year": report.year,
            "month": report.month,
            "quarter": report.quarter,
            "company_info": {
                "company_name": report.company_info.company_name,
                "tax_number": report.company_info.tax_number,
                "industry": report.company_info.industry
            }
        } for report in company_reports]
    }
