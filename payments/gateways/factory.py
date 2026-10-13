from payments.models import Gateway
from payments.gateways.test import TestGateway
from payments.gateways.fake import FakeGateway

GATEWAY_CLASSES = {
    Gateway.TEST: TestGateway,
    Gateway.FAKE: FakeGateway,
}

def get_gateway(gateway_type):
    gateway_class = GATEWAY_CLASSES.get(gateway_type)
    
    if gateway_class is None:
        raise ValueError(
            f"درگاه پرداخت پشتیبانی نمی شود: {gateway_type}"
        )
    return gateway_class()
    
def get_default_gateway():
    return Gateway.TEST

