from pydantic import BaseModel


class VendorOnboarding(BaseModel):
    full_name: str
    phone_number: str
    address: str
    business_name: str
