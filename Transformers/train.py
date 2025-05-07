# train.py

import json
from datasets import Dataset, DatasetDict
from transformers import T5ForConditionalGeneration, T5Tokenizer, Trainer, TrainingArguments
import torch

# --------------------------------------------------------------
# 1. Load raw data from your JSON file
# --------------------------------------------------------------
with open("my_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# data is expected to be a list of dicts like:
# [
#   {
#       "ID": 1,
#       "en": "What is Room5.02?",
#       "sparql": "SELECT ?type WHERE ...",
#       "response": "type: brick:Room ...",
#       "explanation": "Room5.02 is identified as a `brick:Room` ..."
#   },
#   ...
# ]

# --------------------------------------------------------------
# 2. Create the training entries for each task
# --------------------------------------------------------------
inputs = []
targets = []

for example in data:
    user_question = example.get("en", "")
    sparql_query  = example.get("sparql", "")
    response      = example.get("response", "")
    explanation   = example.get("explanation", "")

    # 2A) NL->SPARQL
    # Input:  "Translate: <en>"
    # Target: <sparql>
    if user_question and sparql_query:
        inputs.append(f"Translate: {user_question}")
        targets.append(sparql_query)

    # 2B) Summarization (Explanation of SPARQL results)
    # Input:  "Summarize: <en> <response>"
    # Target: <explanation>
    # Only if response + explanation are present
    if user_question and response and explanation:
        inputs.append(f"Summarize: {user_question} {response}")
        targets.append(explanation)

    # 2C) General Q&A (optional)
    # Input:  "Answer: <en>"
    # Target: <explanation> (or some other text if you prefer)
    if user_question and explanation:
        inputs.append(f"Answer: {user_question}")
        targets.append(explanation)

# Now we have a list of input-target pairs for all tasks
print(f"Created {len(inputs)} examples total from {len(data)} original records.")

# --------------------------------------------------------------
# 3. Build a Hugging Face Dataset
# --------------------------------------------------------------
# We'll keep it simple and treat all as a single "train" split.
train_dataset = Dataset.from_dict({
    "input_text": inputs,
    "target_text": targets
})

# If you have a separate validation set, you could create or split here
dataset = DatasetDict({
    "train": train_dataset
    # "validation": ...
})

# --------------------------------------------------------------
# 4. Load a T5 model and tokenizer
# --------------------------------------------------------------
model_name = "t5-small"  # or "t5-base", "google/flan-t5-base", etc.
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

# --------------------------------------------------------------
# 5. Preprocess (tokenize) for T5
# --------------------------------------------------------------
def preprocess_function(examples):
    model_inputs = tokenizer(
        examples["input_text"], 
        max_length=512, 
        truncation=True
    )
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            examples["target_text"], 
            max_length=512, 
            truncation=True
        )
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(preprocess_function, batched=True)

# --------------------------------------------------------------
# 6. Training Arguments & Trainer
# --------------------------------------------------------------
training_args = TrainingArguments(
    output_dir="T5-unified/trained",  # Where to save checkpoints
    overwrite_output_dir=True,
    evaluation_strategy="no",         # For demonstration, no eval
    num_train_epochs=3,
    per_device_train_batch_size=2,
    save_steps=5000,
    logging_steps=100,
    learning_rate=5e-5,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    tokenizer=tokenizer,
)

# --------------------------------------------------------------
# 7. Train
# --------------------------------------------------------------
trainer.train()

# --------------------------------------------------------------
# 8. Save final model
# --------------------------------------------------------------
trainer.save_model("T5-unified/trained")
tokenizer.save_pretrained("T5-unified/trained")

print("Training complete. Model and tokenizer saved to T5-unified/trained.")
