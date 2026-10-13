from payments.gateways.base import BaseGateway

class FakeGateway(BaseGateway):
    def create_payment(self, payment):
        return {
            "success": True,
            "authority": f"FAKE-AUTH-{payment.id}"
        }
        
    def verify_payment(self, payment):
        return {
            "success": True,
            "amount": payment.amount,
            "reference_id": f"FAKE-{payment.id}",
        }