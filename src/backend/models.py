class Response:
    def __init__(self, data, status, message):
        self.data = data
        self.status = status
        self.message = message

    def to_json(self):
        return {
            'status': self.status,
            'message': self.message,
            'data': self.data
        }

