class BaseGateway:
    
    def create_payment(self,payment):
        raise NotImplementedError
    
    def verify_payment(self, payment, **kwargs):
        raise NotImplementedError
    