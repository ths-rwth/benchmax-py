class BenchmaxException(Exception):
    def __init__(self, msg):
        self.__msg = msg

    def __str__(self):
        return "[benchmax][ERROR]: {}".format(self.__msg)