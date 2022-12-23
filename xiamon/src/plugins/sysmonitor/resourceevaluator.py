from collections import deque
from statistics import mean

class Resourceevaluator():
    def __init__(self, config):
        self.__treshold = config['treshold']
        self.__lower_treshold = self.__treshold - config['hysteresis']
        self.__samples = config['samples']

        self.__buffer = deque([0.0]*self.__samples, self.__samples)
        self.__above_treshold = False

    def update(self, value):
        self.__buffer.append(value)
        avg = mean(self.__buffer)
        treshold = self.__treshold if not self.__above_treshold else self.__lower_treshold
        self.__above_treshold = avg > treshold
        return avg

    @property
    def treshold_exceeded(self):
        return self.__above_treshold