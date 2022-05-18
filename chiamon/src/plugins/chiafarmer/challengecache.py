import datetime
import yaml
import ciso8601
from ...core import Plugin

class ChallengeCache:
    def __init__(self, plugin, file, aggregation):
        self.__plugin = plugin
        self.aggregation = aggregation
        self.__file = file
        self.__current_challenge = None
        self.__challenges = dict()
        self.__read_file()

    def add_point(self, hash, index):
        if hash in self.__challenges:
            self.__challenges[hash].update(index)
        elif self.__current_challenge is None:
            self.__current_challenge = ChallengeCache.Challenge(hash)
            self.__current_challenge.update(index)
        elif self.__current_challenge.hash == hash:
            self.__current_challenge.update(index)
        else:
            self.__challenges[self.__current_challenge.hash] = self.__current_challenge
            self.__current_challenge = ChallengeCache.Challenge(hash)
            self.__current_challenge.update(index)

    def get_factor(self, whole_day=True):
        hour_delta = self.aggregation if whole_day else 1
        time_limit = datetime.datetime.now() - datetime.timedelta(hours=hour_delta)
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

    async def cleanup(self):
        old_len = len(self.__challenges)
        oldest_timestamp = datetime.datetime.now() - datetime.timedelta(hours=(self.aggregation + 1))
        self.__challenges = {k: v for k, v in self.__challenges.items() if v.time > oldest_timestamp}
        cleared = old_len - len(self.__challenges)
        await self.__plugin.send(Plugin.Channel.debug, f"Cleared {cleared} item(s) from challenge cache.")

    async def save(self):
        await self.__write_file()

    def __read_file(self):
        try:
            with open(self.__file, "r") as stream:
                data = yaml.safe_load(stream)

            challenge_count = 0
            for challenge in data.values():
                self.__challenges[challenge['hash']] = ChallengeCache.Challenge.from_file(challenge)
                challenge_count += 1
            self.__plugin.print(f'Imported {challenge_count} challenge(s) from {self.__file}')
        except Exception as e:
            self.__plugin.print(f'Reading config file {self.__file} failed: {e}')

    async def __write_file(self):
        data = {}
        for hash, challenge in self.__challenges.items():
            challenge_as_dict = {'hash': challenge.hash, 'points': list(challenge.points), 'timestamp': challenge.time.strftime("%Y-%m-%dT%H:%M:%S")}
            data[hash] = challenge_as_dict
        with open(self.__file, "w") as stream:
            yaml.safe_dump(data, stream)
        await self.__plugin.send(Plugin.Channel.debug, f"Wrote {len(data)} challenge(s) to {self.__file}")

    class Challenge:
        def __init__(self, hash):
            self.time = datetime.datetime.now()
            self.hash = hash
            self.points = set()

        @classmethod
        def from_file(cls, challenge):
            instance = cls(challenge['hash'])
            instance.time = ciso8601.parse_datetime(challenge['timestamp'])
            instance.points = set(challenge['points'])
            return instance

        def update(self, point):
            self.points.add(point)

