class RippleError(Exception):
    def __init__(self, message, data):
        super(RippleError, self).__init__(message)

        self.message = message
        self.data = data

    def __str__(self):
        result = '[(' + self.message
        if self.data:
            result += ', ' + str(self.data)

        result += ')]'
        return result


class UnexpectedError(RippleError):
    pass


class LedgerVersionError(RippleError):
    pass


class ConnectionError(RippleError):
    pass


class NotConnectedError(ConnectionError):
    pass


class DisconnectedError(ConnectionError):
    pass


class RippledNotInitializedError(ConnectionError):
    pass


class TimeoutError(ConnectionError):
    pass


class ResponseFormatError(ConnectionError):
    pass


class ValidationError(RippleError):
    pass


class NotFoundError(RippleError):
    def __init__(self):
        super(NotFoundError, self).__init__(message='Not found')


class MissingLedgerHistoryError(RippleError):
    def __init__(self):
        super(MissingLedgerHistoryError, self).__init__(
            message='Server is missing ledger history in the specified range')


class PendingLedgerVersionError(RippleError):
    def __init__(self):
        super(PendingLedgerVersionError, self).__init__(
            message='maxLedgerVersion is greater than server\'s most recent validated ledger')
