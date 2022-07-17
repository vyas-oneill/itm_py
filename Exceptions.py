class ItmException(Exception):
    pass


class IntelligenceTransferFailedException(ItmException):
    pass


class StrategyDecidedNotToResolveException(ItmException):
    pass


class EncapsulationNotSupportedException(ItmException):
    pass

class InvalidMessageFormatException(ItmException):
    pass