import re
from typing import Dict

try:
    import spacy
    _NLP = spacy.load("en_core_web_sm")
except Exception:
    _NLP = None

class EntityExtractor:
    def extract(self, text: str) -> Dict:
        t = text.lower()
        entities: Dict[str, str] = {}

        # Components / parameters (regex-lite rules)
        for c in ["foundation", "wall", "beam", "roof", "column"]:
            if c in t:
                entities["component"] = c
                break

        for p in ["thickness", "height", "width", "length", "slope"]:
            if p in t:
                entities["parameter"] = p
                break

        m = re.search(r"(\d+\.?\d*\s*(mm|cm|m|kg|ton|%)?)", t)
        if m:
            entities["value"] = m.group(1)

        m2 = re.search(r"(north|south|east|west|center|middle)", t)
        if m2:
            entities["location"] = m2.group(1)

        # spaCy NER (optional)
        if _NLP:
            doc = _NLP(text)
            spacy_entities = []
            for ent in doc.ents:
                if ent.label_ in ["QUANTITY", "CARDINAL", "ORDINAL", "GPE", "LOC"]:
                    spacy_entities.append({"text": ent.text, "label": ent.label_})
            if spacy_entities:
                entities["spacy_entities"] = spacy_entities

        return entities

entity_extractor = EntityExtractor()
