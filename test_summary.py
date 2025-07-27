from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

# Load tokenizer and model
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

# Text to summarize
input_text = "Summarize: Jessie spent the whole day learning transformers and is now trying FLAN-T5."

# Tokenize the input
inputs = tokenizer(input_text, return_tensors="pt")

# Generate summary
outputs = model.generate(**inputs, max_new_tokens=50)

# Decode and print the summary
summary = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("Summary:", summary)
