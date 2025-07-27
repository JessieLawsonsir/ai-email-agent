from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# ✅ Load FLAN-T5 model and tokenizer
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# ✅ Sample emails to summarize
emails = [
    "Hi, I ordered a laptop two weeks ago and it still hasn't arrived. Can you check the delivery status?",
    "I received the wrong product in my last order. Please advise on what to do.",
    "Can I change the delivery address for my recent purchase?",
    "The item I bought is damaged. I need a replacement or refund.",
]

# ✅ Instruction-style prompt (few-shot learning)
instruction = """Summarize this customer support email:
Customer: I received the wrong product in my last order. Please advise on what to do.
Summary: Customer received incorrect product and wants guidance.

Summarize this customer support email:
Customer: {email}
Summary:"""

# ✅ Generate summaries
for i, email in enumerate(emails, 1):
    prompt = instruction.format(email=email)
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True)
    outputs = model.generate(**inputs, max_new_tokens=50)
    summary = tokenizer.decode(outputs[0], skip_special_tokens=True)

    print(f"\n📩 Email {i}: {email}")
    print(f"📝 Summary: {summary}")
