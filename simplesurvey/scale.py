import yaml


class OrdinalScale:

    def __init__(self, labels=None, ratings=None, default_value=0):
        assert len(labels) == len(ratings), "All labels need an associated rating"

        if labels is None:
            self._labels = []
        self._labels = labels

        if ratings is None:
            self._ratings = []
        self._ratings = ratings

        self._default_value = default_value

    @property
    def ratings(self):
        return self._ratings

    @property
    def labels(self):
        return self._labels

    def scoring(self):
        return {k: v for k, v in zip(self.labels, self.ratings)}


def ordinal_scale_constructor(loader, node):
    values = loader.construct_mapping(node)
    return OrdinalScale(labels=values.get("labels"),
                        ratings=values.get("ratings"))

yaml.add_constructor("!OrdinalScale", ordinal_scale_constructor)
