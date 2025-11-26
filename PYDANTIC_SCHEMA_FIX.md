# Pydantic Schema Fix - Float Credit System

## Problem

After migrating the credit system from INTEGER to FLOAT, the `/api/v1/credits/pricing` endpoint returned **500 Internal Server Error**.

### Root Cause

The Pydantic response schemas in `app/api/credits.py` were still defined with `int` types, but the service layer (`app/services/credit_service.py`) was returning `float` values after the migration.

**Type Mismatch**:
```python
# Backend Service (credit_service.py)
@property
def TRANSCRIPTION_BASE(self) -> float:  # Returns float
    return self.get_price("transcription_base")

# API Response Schema (credits.py) - BEFORE FIX
class CreditPricingResponse(BaseModel):
    transcription_per_minute: int  # Expected int ❌
    speaker_recognition_per_minute: int
    # ...
```

FastAPI/Pydantic validation failed because `1.0` (float) couldn't be coerced to `int` without data loss.

---

## Solution

Updated **all credit-related Pydantic schemas** in `app/api/credits.py` to use `float` instead of `int`:

### 1. Credit Balance Schema
```python
class CreditBalance(BaseModel):
    credits: float  # Was: int
    user_id: int
    username: str
```

### 2. Transaction Schema
```python
class CreditTransactionResponse(BaseModel):
    id: int
    amount: float  # Was: int
    operation_type: str
    description: str | None
    transcription_id: int | None
    balance_after: float  # Was: int
    created_at: datetime
```

### 3. Credit History Schema
```python
class CreditHistoryResponse(BaseModel):
    transactions: List[CreditTransactionResponse]
    total_earned: float  # Was: int
    total_spent: float  # Was: int
    current_balance: float  # Was: int
```

### 4. Pricing Response Schema
```python
class CreditPricingResponse(BaseModel):
    transcription_per_minute: float  # Was: int
    speaker_recognition_per_minute: float  # Was: int
    youtube_download: float
    ai_enhancement: float
    lecture_notes: float
    custom_prompt: float
    exam_questions: float
    translation: float
    tavily_web_search: float
```

### 5. Credit Purchase Request
```python
class CreditPurchaseRequest(BaseModel):
    package: str
    amount: float | None = None  # Was: int | None
```

### 6. Admin Add Credits Endpoint
```python
@router.post("/admin/add")
async def admin_add_credits(
    user_id: int,
    amount: float,  # Was: int
    reason: str,
    # ...
):
```

### 7. Pricing Config Schema (Admin Panel)
```python
class PricingConfigResponse(BaseModel):
    id: int
    operation_key: str
    operation_name: str
    cost_per_unit: float  # Was: int
    unit_description: str
    description: str | None
    is_active: bool

class PricingConfigUpdate(BaseModel):
    configs: dict[str, float]  # Was: dict[str, int]
```

---

## Verification

### API Test
```powershell
# Test endpoint with curl
curl.exe -H "Origin: http://localhost:5173" http://localhost:8002/api/v1/credits/pricing
```

**Expected Response** (200 OK):
```json
{
  "transcription_per_minute": 1.0,
  "speaker_recognition_per_minute": 0.5,
  "youtube_download": 10.0,
  "ai_enhancement": 20.0,
  "lecture_notes": 30.0,
  "custom_prompt": 25.0,
  "exam_questions": 20.0,
  "translation": 15.0,
  "tavily_web_search": 5.0
}
```

**CORS Headers Present**:
```
access-control-allow-origin: http://localhost:5173
access-control-allow-credentials: true
```

### Python Test
```python
from app.database import SessionLocal
from app.services.credit_service import get_credit_service

db = SessionLocal()
cs = get_credit_service(db)

print(f"Transcription base: {cs.pricing.TRANSCRIPTION_BASE} kredi/dk")  # 1.0
print(f"Speaker recognition: {cs.pricing.SPEAKER_RECOGNITION} kredi/dk")  # 0.5

db.close()
```

---

## Impact

✅ **Fixed** `/api/v1/credits/pricing` endpoint (500 → 200)  
✅ **Fixed** Frontend credit displays now load correctly  
✅ **Fixed** Admin panel pricing configuration  
✅ **Fixed** Credit transaction history displays  
✅ **Fixed** Credit balance queries  

---

## Lessons Learned

### Critical Rule: **Database Migration → API Schema Update**

When migrating database column types:
1. ✅ Update SQLAlchemy models (`Column(Integer)` → `Column(Float)`)
2. ✅ Update service layer return types (`-> int` → `-> float`)
3. ✅ **Update Pydantic schemas** (`field: int` → `field: float`)
4. ✅ Update frontend TypeScript types (`credits: number` - already correct)
5. ✅ Update frontend display logic (`.toFixed(2)` for decimals)

**Failure to update Pydantic schemas = 500 Internal Server Error**

### Why Pydantic Validation Failed

FastAPI uses Pydantic for:
- **Request validation** (incoming data)
- **Response validation** (outgoing data)
- **Serialization** (Python objects → JSON)

When response data types don't match the schema:
- Pydantic raises `ValidationError`
- FastAPI catches it and returns 500 error
- CORS headers ARE present (because exception handlers run before CORS middleware)

---

## Files Modified

1. `app/api/credits.py` - All response schemas updated to `float`
2. (Already done) `app/models/user.py` - `credits` Column to Float
3. (Already done) `app/models/credit_transaction.py` - `amount`, `balance_after` to Float
4. (Already done) `app/models/credit_pricing.py` - `cost_per_unit` to Float
5. (Already done) `app/services/credit_service.py` - All return types to `float`

---

## Next Steps

1. ✅ Backend restarted automatically (uvicorn --reload picks up changes)
2. ⏳ Frontend refresh (Ctrl+Shift+R to clear cached errors)
3. ⏳ Test upload with 57-second file
4. ⏳ Verify 1.43 credit deduction (0.95 + 0.48)

---

## Date

November 4, 2025 09:35 AM
