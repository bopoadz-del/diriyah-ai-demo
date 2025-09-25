from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
import os

class IntentClassifier:
    def __init__(self, model_dir="backend/models"):
        self.model_path = os.path.join(model_dir, "intent_model.pkl")
        self.vectorizer_path = os.path.join(model_dir, "vectorizer.pkl")
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            self.model = joblib.load(self.model_path)
            self.vectorizer = joblib.load(self.vectorizer_path)
        else:
            self.model, self.vectorizer = None, None

    def predict(self, text: str):
        if not self.model or not self.vectorizer:
            return None, 0.0
        X = self.vectorizer.transform([text])
        probs = self.model.predict_proba(X)[0]
        label = self.model.classes_[probs.argmax()]
        confidence = probs.max()
        return label, confidence

classifier = IntentClassifier()
