
class Drivestate:

    def __init__(self, max_countdown):
        self.__max_countdown = max_countdown
        self.__countdown = self.__max_countdown
        self.__active = 0
        self.__pings = 0

    def reset_statistics(self):
        self.__active = 0
        self.__pings = 0

    def unavailable(self):
        self.__countdown = 0

    def inactive(self):
        self.__countdown -= 1
        self.__countdown = max(self.__countdown, 0)

    def active(self):
        self.__active += 1
        if self.__countdown == 0:
            return
        self.__countdown = self.__max_countdown

    def pinged(self, success):
        self.__pings += 1
        if success:
            self.__countdown = self.__max_countdown
        else:
            self.__countdown = 0

    @property
    def countdown(self):
        return self.__countdown

    @property
    def online(self):
        return self.__countdown > 0

    @property
    def active_count(self):
        return self.__active

    @property
    def ping_count(self):
        return self.__pings

    @property
    def ping_outstanding(self):
        return self.__countdown == 0
   