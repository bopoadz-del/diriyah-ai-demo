import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

training_data = {
    "cad_takeoff": ["run cad takeoff","extract cad quantities","process dxf"],
    "boq_parser": ["parse boq","upload boq excel","read bill of quantities"],
    "primavera": ["import xer","analyze primavera schedule","check p6 schedule"],
    "bim": ["process ifc","analyze bim model","bim integration"],
    "aconex": ["search aconex","get aconex docs"],
    "vision": ["analyze photo","yolo detection","site image check"],
    "consolidated_takeoff": ["merge cad and boq","consolidated quantities"],
    "analytics_engine": ["project kpi report","analytics dashboard"],
    "alerts_engine": ["raise alert","compliance alert"],
    "rag_engine": ["semantic search","query project data"]
}

X, y = [], []
for label, phrases in training_data.items():
    for p in phrases:
        X.append(p)
        y.append(label)

vectorizer = TfidfVectorizer()
X_vec = vectorizer.fit_transform(X)
model = LogisticRegression(max_iter=500)
model.fit(X_vec, y)

model_dir = os.path.join("backend", "models")
os.makedirs(model_dir, exist_ok=True)
joblib.dump(model, os.path.join(model_dir, "intent_model.pkl"))
joblib.dump(vectorizer, os.path.join(model_dir, "vectorizer.pkl"))

print("✅ Intent model trained and saved to backend/models/")
