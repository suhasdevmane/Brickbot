from rasa.nlu.components import Component
from rapidfuzz import process, fuzz


class FuzzySensorMatcher(Component):
    def __init__(self, component_config=None):
        super().__init__(component_config)
        self.threshold = component_config.get("threshold", 0.8)
        with open("data/sensor_list.txt", "r") as f:
            self.sensor_list = [line.strip() for line in f]

    def process(self, message, **kwargs):
        entities = message.get("entities", [])
        for entity in entities:
            if entity["entity"] == "sensor_type":
                candidate = entity["value"]
                best_match, score, _ = process.extractOne(
                    candidate, self.sensor_list, scorer=fuzz.ratio
                )
                if score / 100 >= self.threshold:
                    entity["value"] = best_match
                    entity["confidence"] = score / 100
        message.set("entities", entities)

    @classmethod
    def required_packages(cls):
        return ["rapidfuzz"]
