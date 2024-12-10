from sqlalchemy.orm import Session, contains_eager
from sqlalchemy import func
from models import Channel, User, CompanyReport, ReportTransaction, CompanyInfo
from typing import List, Optional
from datetime import datetime

def get_channel_by_id(db: Session, channel_id: int) -> Optional[Channel]:
    return db.query(Channel).filter(Channel.id == channel_id).first()

def get_channel_by_number(db: Session, channel_number: str) -> Optional[Channel]:
    return db.query(Channel).filter(Channel.channel_number == channel_number).first()

def get_channel_users(db: Session, channel_id: int) -> List[User]:
    return db.query(User).filter(User.channel_id == channel_id).all()

def get_channel_second_level_users(db: Session, channel_id: int) -> List[User]:
    return db.query(User).filter(
        User.channel_id == channel_id,
        User.role == "level_2"
    ).all()

def get_channel_reports(db: Session, channel_id: int) -> List[dict]:
    # Get all users belonging to this channel
    channel_users = db.query(User.id).filter(User.channel_id == channel_id).subquery()
    
    # Get all reports processed by these users, including company info
    reports = (
        db.query(CompanyReport, CompanyInfo)
        .join(channel_users, CompanyReport.processed_by_user_id == channel_users.c.id)
        .join(
            CompanyInfo,
            CompanyReport.company_tax_number == CompanyInfo.tax_number
        )
        .order_by(CompanyReport.created_at.desc())
        .all()
    )
    
    # Format the results
    formatted_reports = []
    for report, company_info in reports:
        formatted_reports.append({
            'id': report.id,
            'report_type': report.report_type,
            'year': report.year,
            'month': report.month,
            'quarter': report.quarter,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'company_info': {
                'company_name': company_info.company_name,
                'tax_number': company_info.tax_number,
                'industry': company_info.industry,
                'registration_type': company_info.registration_type,
                'taxpayer_nature': company_info.taxpayer_nature
            },
            'processed_by_user': {
                'id': report.processed_by_user_id
            }
        })
    
    return formatted_reports

def get_report_details(db: Session, report_id: int, user_channel_id: int) -> Optional[dict]:
    # Get the report with company info and verify it belongs to the channel
    result = (
        db.query(CompanyReport, CompanyInfo, User)
        .join(User, CompanyReport.processed_by_user_id == User.id)
        .join(
            CompanyInfo,
            CompanyReport.company_tax_number == CompanyInfo.tax_number
        )
        .filter(
            CompanyReport.id == report_id,
            User.channel_id == user_channel_id
        )
        .first()
    )
    
    if not result:
        return None
        
    report, company_info, user = result
    
    return {
        'report': {
            'id': report.id,
            'report_type': report.report_type,
            'year': report.year,
            'month': report.month,
            'quarter': report.quarter,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'report_data': report.report_data,
            'processed_by_user_id': report.processed_by_user_id
        },
        'company_info': {
            'company_name': company_info.company_name,
            'tax_number': company_info.tax_number,
            'industry': company_info.industry,
            'registration_type': company_info.registration_type,
            'taxpayer_nature': company_info.taxpayer_nature,
            'index_standard_type': company_info.index_standard_type
        }
    }

def get_user_reports(db: Session, user_id: int) -> List[CompanyReport]:
    return (
        db.query(CompanyReport)
        .filter(CompanyReport.processed_by_user_id == user_id)
        .join(
            CompanyInfo,
            CompanyReport.company_tax_number == CompanyInfo.tax_number,
            isouter=True  # Use left outer join
        )
        .options(
            contains_eager(CompanyReport.company_info)
        )
        .order_by(CompanyReport.created_at.desc())
        .all()
    )

def get_channel_transactions(db: Session, channel_id: int) -> List[ReportTransaction]:
    return db.query(ReportTransaction).filter(
        ReportTransaction.channel_id == channel_id
    ).order_by(ReportTransaction.created_at.desc()).all()

def get_channel_statistics(db: Session, channel_id: int) -> dict:
    # Get upload and download counts
    transactions = db.query(
        ReportTransaction.transaction_type,
        func.count(ReportTransaction.id).label('count'),
        func.sum(ReportTransaction.cost).label('total_cost')
    ).filter(
        ReportTransaction.channel_id == channel_id
    ).group_by(ReportTransaction.transaction_type).all()

    stats = {
        'total_uploads': 0,
        'total_downloads': 0,
        'total_cost': 0.0
    }

    for transaction_type, count, cost in transactions:
        if transaction_type == 'upload':
            stats['total_uploads'] = count
        elif transaction_type == 'download':
            stats['total_downloads'] = count
        stats['total_cost'] += float(cost or 0)

    return stats

def get_channel_dashboard_data(db: Session, channel_id: int) -> dict:
    channel = get_channel_by_id(db, channel_id)
    if not channel:
        return None

    second_level_users = get_channel_second_level_users(db, channel_id)
    reports = get_channel_reports(db, channel_id)
    recent_transactions = get_channel_transactions(db, channel_id)[:10]  # Get last 10 transactions
    statistics = get_channel_statistics(db, channel_id)

    return {
        'channel': channel,
        'second_level_users': second_level_users,
        'reports': reports,
        'recent_transactions': recent_transactions,
        **statistics
    }

def get_level2_user_reports_data(db: Session, user_id: int) -> dict:
    # Get the user with their channel information
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "level_2":
        return None

    # Get the user's reports with company info
    reports = get_user_reports(db, user_id)

    # Convert to dictionary format
    return {
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'firstname': user.firstname,
            'lastname': user.lastname,
            'role': user.role,
            'channel_id': user.channel_id
        },
        'reports': [{
            'id': report.id,
            'report_type': report.report_type,
            'year': report.year,
            'month': report.month,
            'quarter': report.quarter,
            'created_at': report.created_at.isoformat() if report.created_at else None,
            'company_info': {
                'company_name': report.company_info.company_name if report.company_info else 'Unknown Company',
                'tax_number': report.company_tax_number
            }
        } for report in reports]
    }

def update_channel_balance(db: Session, channel_id: int, amount: float) -> Optional[Channel]:
    channel = get_channel_by_id(db, channel_id)
    if not channel:
        return None
    
    channel.balance += amount
    db.commit()
    db.refresh(channel)
    return channel

def create_report_transaction(
    db: Session,
    user_id: int,
    channel_id: int,
    report_id: int,
    transaction_type: str,
    cost: float
) -> ReportTransaction:
    transaction = ReportTransaction(
        user_id=user_id,
        channel_id=channel_id,
        report_id=report_id,
        transaction_type=transaction_type,
        cost=cost,
        created_at=datetime.utcnow()
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction
