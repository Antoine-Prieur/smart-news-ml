import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(
    "nlptown/bert-base-multilingual-uncased-sentiment"
)
model = AutoModelForSequenceClassification.from_pretrained(
    "nlptown/bert-base-multilingual-uncased-sentiment"
)

text = "I love this product! It's amazing."
inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)

with torch.no_grad():
    outputs = model(**inputs)
    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

predicted_class = torch.argmax(predictions, dim=-1).item()
confidence = predictions[0][predicted_class].item()

print(f"Text: {text}")
print(f"Predicted sentiment class: {predicted_class}")
print(f"Confidence: {confidence:.4f}")

star_rating = predicted_class + 1
print(f"Star rating: {star_rating}/5")
