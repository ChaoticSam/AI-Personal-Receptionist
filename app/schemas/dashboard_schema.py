from pydantic import BaseModel
from typing import List, Optional


class DayCount(BaseModel):
    day: str
    count: int


class RecentCall(BaseModel):
    id: str
    phone: str
    time: str
    status: str


class DashboardStats(BaseModel):
    total_calls: int
    total_orders: int
    total_products: int
    total_customers: int
    calls_this_week: List[DayCount]
    orders_this_week: List[DayCount]
    recent_calls: List[RecentCall]
