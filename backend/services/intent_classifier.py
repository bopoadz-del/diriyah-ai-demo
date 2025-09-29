class _DummyClassifier:
    def predict(self, text: str):
        return ("unknown", 0.0)
classifier = _DummyClassifier()
