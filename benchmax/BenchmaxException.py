class BenchmaxException(Exception):
    def __init__(self, msg):
        self.__msg = msg

    def __str__(self):
        return "Exception: {}".format(self.__msg)
