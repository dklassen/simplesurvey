

class OrdinalScale:
    """ Represents a ordinal scale with a mapping to a numerical value"""

    def __init__(self, labels=None, ratings=None, default_value=0):
        if labels is None:
            self._labels = []

        if ratings is None:
            self._ratings = []

        assert len(labels) == len(ratings), "All labels need an associated rating"

        self._labels = labels
        self._ratings = ratings
        self._default_value = 0

    @property
    def ratings(self):
        return self._ratings

    @property
    def labels(self):
        return self._labels

    def scoring(self):
        return {k: v for k, v in zip(self.labels, self.ratings)}
