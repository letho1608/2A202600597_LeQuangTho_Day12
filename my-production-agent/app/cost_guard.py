import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.config import settings


class CostGuard:
    INPUT_TOKEN_PRICE = 0.15 / 1_000_000
    OUTPUT_TOKEN_PRICE = 0.60 / 1_000_000
    AVG_INPUT_TOKENS = 200
    AVG_OUTPUT_TOKENS = 150

    def __init__(self, monthly_budget: float = 10.0):
        self.monthly_budget = monthly_budget
        self._usage: dict[str, float] = {}

    def _get_month_key(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def _get_user_key(self, user_id: str) -> str:
        return f"{user_id}:{self._get_month_key()}"

    def estimate_cost(self) -> float:
        input_cost = self.AVG_INPUT_TOKENS * self.INPUT_TOKEN_PRICE
        output_cost = self.AVG_OUTPUT_TOKENS * self.OUTPUT_TOKEN_PRICE
        return input_cost + output_cost

    def check_budget(self, user_id: str) -> None:
        key = self._get_user_key(user_id)
        current = self._usage.get(key, 0.0)
        estimated = self.estimate_cost()

        if current + estimated > self.monthly_budget:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "budget_exceeded",
                    "message": f"Monthly budget ${self.monthly_budget:.2f} exceeded.",
                    "current_spend": round(current, 4),
                    "estimated_cost": round(estimated, 6),
                    "budget": self.monthly_budget,
                    "reset": self._get_month_key(),
                },
            )

    def record_usage(self, user_id: str, input_tokens: int = AVG_INPUT_TOKENS, output_tokens: int = AVG_OUTPUT_TOKENS) -> dict:
        input_cost = input_tokens * self.INPUT_TOKEN_PRICE
        output_cost = output_tokens * self.OUTPUT_TOKEN_PRICE
        total_cost = input_cost + output_cost

        key = self._get_user_key(user_id)
        self._usage[key] = self._usage.get(key, 0.0) + total_cost

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": round(total_cost, 6),
            "total_spent": round(self._usage[key], 4),
        }

    def get_usage(self, user_id: str) -> dict:
        key = self._get_user_key(user_id)
        current = self._usage.get(key, 0.0)
        return {
            "user_id": user_id,
            "period": self._get_month_key(),
            "current_spend": round(current, 4),
            "budget": self.monthly_budget,
            "remaining": round(max(0, self.monthly_budget - current), 4),
            "usage_percent": round((current / self.monthly_budget) * 100, 2) if self.monthly_budget > 0 else 0,
        }


cost_guard = CostGuard(monthly_budget=settings.DAILY_BUDGET_USD)


async def check_budget(user_id: str = None) -> None:
    cost_guard.check_budget(user_id or "anonymous")
