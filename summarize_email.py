from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# Load model and tokenizer once
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Sample emails to summarize
emails = [
    "Hi, I ordered a laptop two weeks ago and it still hasn't arrived. Can you check the delivery status?",
    "I received the wrong product in my last order. Please advise on what to do.",
    "Can I change the delivery address for my recent purchase?",
    "The item I bought is damaged. I need a replacement or refund.",
]

# Optional: few-shot prompt for better summaries
instruction = """Summarize this customer support email:
Customer: I received the wrong product in my last order. Please advise on what to do.
Summary: Customer received incorrect product and wants guidance.

Summarize this customer support email:
Customer: {email}
Summary:"""

# Loop through each email and summarize
for i, email in enumerate(emails, 1):
    full_prompt = instruction.format(email=email)

    inputs = tokenizer(full_prompt, return_tensors="pt", truncation=True)
    output = model.generate(**inputs, max_new_tokens=50)
    summary = tokenizer.decode(output[0], skip_special_tokens=True)

    print(f"\n📩 Email {i}: {email}")
    print(f"📝 Summary: {summary}")
