
# # Load the BLEU and ROUGE metrics
# bleu_metric = evaluate.load("bleu")
# rouge_metric = evaluate.load("rouge")

# # Example sentences (non-tokenized)
# reference = ["the cat is on the mat"]
# candidate = ["the woman is sitting, jumping, playing on the mat"]

# # BLEU expects plain text inputs
# bleu_results = bleu_metric.compute(predictions=candidate, references=reference, max_order=1)
# print(f"BLEU Score: {bleu_results['bleu'] * 100:.2f}")

# # ROUGE expects plain text inputs
# rouge_results = rouge_metric.compute(predictions=candidate, references=reference)

# # Access ROUGE scores (no need for indexing into the result)
# print(f"ROUGE-1 F1 Score: {rouge_results['rouge1']:.2f}")
# print(f"ROUGE-L F1 Score: {rouge_results['rougeL']:.2f}")