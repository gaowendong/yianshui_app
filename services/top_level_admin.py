from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict, Optional
from models import User, Channel, CompanyReport, CompanyInfo
from fastapi import HTTPException

class TopLevelAdminService:
    @staticmethod
    def get_dashboard_stats(db: Session) -> Dict:
        """Get overall statistics for the dashboard"""
        total_channels = db.query(Channel).count()
        total_users = db.query(User).count()
        total_reports = db.query(CompanyReport).count()
        
        return {
            "total_channels": total_channels,
            "total_users": total_users,
            "total_reports": total_reports
        }

    @staticmethod
    def get_all_channels(db: Session) -> List[Dict]:
        """Get all channels with their users and reports"""
        channels = db.query(Channel).all()
        
        result = []
        for channel in channels:
            channel_data = {
                "id": channel.id,
                "channel_number": channel.channel_number,
                "channel_name": channel.channel_name,
                "channel_location": channel.channel_location,
                "users": [],
                "total_reports": 0
            }
            
            # Get all users for this channel
            for user in channel.users:
                user_data = {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "reports_count": len(user.company_reports)
                }
                channel_data["users"].append(user_data)
                channel_data["total_reports"] += user_data["reports_count"]
            
            result.append(channel_data)
        
        return result

    @staticmethod
    def get_channel_details(db: Session, channel_id: int) -> Dict:
        """Get detailed information about a specific channel"""
        channel = db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        return {
            "id": channel.id,
            "channel_number": channel.channel_number,
            "channel_name": channel.channel_name,
            "channel_location": channel.channel_location,
            "industry": channel.industry,
            "contact_person": channel.contact_person,
            "contact_number": channel.contact_number,
            "email": channel.email,
            "website": channel.website,
            "app": channel.app,
            "official_account": channel.official_account,
            "douyin_account": channel.douyin_account,
            "balance": channel.balance,
            "users": [{
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "reports": [{
                    "id": report.id,
                    "company_name": report.company_info.company_name,
                    "report_type": report.report_type,
                    "year": report.year,
                    "month": report.month,
                    "quarter": report.quarter,
                    "created_at": report.created_at
                } for report in user.company_reports]
            } for user in channel.users]
        }

    @staticmethod
    def get_user_reports(db: Session, user_id: int) -> List[Dict]:
        """Get all reports for a specific user"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return [{
            "id": report.id,
            "company_name": report.company_info.company_name,
            "tax_number": report.company_info.tax_number,
            "report_type": report.report_type,
            "year": report.year,
            "month": report.month,
            "quarter": report.quarter,
            "report_data": report.report_data,
            "created_at": report.created_at,
            "updated_at": report.updated_at
        } for report in user.company_reports]

    @staticmethod
    def get_report_details(db: Session, report_id: int) -> Dict:
        """Get detailed information about a specific report"""
        report = db.query(CompanyReport).filter(CompanyReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        return {
            "id": report.id,
            "company_name": report.company_info.company_name,
            "tax_number": report.company_info.tax_number,
            "report_type": report.report_type,
            "year": report.year,
            "month": report.month,
            "quarter": report.quarter,
            "report_data": report.report_data,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "processed_by": {
                "id": report.processed_by_user.id,
                "username": report.processed_by_user.username,
                "role": report.processed_by_user.role
            },
            "company_info": {
                "industry": report.company_info.industry,
                "registration_type": report.company_info.registration_type,
                "taxpayer_nature": report.company_info.taxpayer_nature,
                "index_standard_type": report.company_info.index_standard_type
            }
        }

    @staticmethod
    def check_top_level_admin(user: User) -> bool:
        """Check if user is a top level admin"""
        return user.is_top_level_admin
