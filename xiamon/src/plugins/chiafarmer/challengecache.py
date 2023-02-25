import datetime

class ChallengeCache:
    def __init__(self, plugin):
        self.__plugin = plugin
        self.__last_cleanup = datetime.datetime.now()
        self.__current_challenge = None
        self.__challenges = dict()

    def add_point(self, hash, index):
        if hash in self.__challenges:
            self.__challenges[hash].update(index)
        elif self.__current_challenge is None:
            # First signage point after startup. We do not know the full challenge,
            # so we mark its previous signage points as complete to prevent false 
            # positive harvest factor alerts.
            self.__current_challenge = ChallengeCache.Challenge(hash)
            for i in range(index, 64):
                self.__current_challenge.update(i)
        elif self.__current_challenge.hash == hash:
            self.__current_challenge.update(index)
        else:
            self.__challenges[self.__current_challenge.hash] = self.__current_challenge
            self.__current_challenge = ChallengeCache.Challenge(hash)
            self.__current_challenge.update(index)

    def get_factor(self, interval):
        time_limit = datetime.datetime.now() - interval
        oldest_timestamp = datetime.datetime.now()

        expected = 0
        actual = 0
        for challenge in self.__challenges.values():
            oldest_timestamp = min(oldest_timestamp, challenge.time)
            if challenge.time < time_limit:
                continue
            expected += 64
            actual += len(challenge.points)

        if oldest_timestamp >= time_limit or expected == 0:
            return None
        else:
            return actual / float(expected)

    def cleanup(self):
        old_len = len(self.__challenges)
        self.__challenges = {k: v for k, v in self.__challenges.items() if v.time > self.__last_cleanup}
        cleared = old_len - len(self.__challenges)
        self.__plugin.msg.debug(f"Cleared {cleared} item(s) from challenge cache.")
        self.__last_cleanup = datetime.datetime.now()

    class Challenge:
        def __init__(self, hash):
            self.time = datetime.datetime.now()
            self.hash = hash
            self.points = set()

        def update(self, point):
            self.points.add(point)

