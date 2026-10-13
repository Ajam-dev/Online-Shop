from payments.gateways.base import BaseGateway
from payments.models import Status as PaymentStatus

class TestGateway(BaseGateway):
    def create_payment(self, payment):
        return {
            "success" : True,
            "authority": f"TEST-AUTH-{payment.id}",
        }
    def verify_payment(self, payment, result = None):
        if result == "failed":
            return {
                "success": False,
                "amount": payment.amount,
                "reference_id": "",
            }
        return {
            "success": True,
            "amount": payment.amount,
            "reference_id" : f"TEST-{payment.id}"
        }