from pathlib import Path

import torch
from captum.attr import LayerGradCam

from model.transformer import MAX_LENGTH, TransformerClassifier, tokenizer


def analyze_text_with_gradcam(text: str) -> list[dict[str, float]]:
    # Load model and weights
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = TransformerClassifier(
        vocab_size=tokenizer.vocab_size, d_model=256, nhead=8, num_layers=6, dim_feedforward=1024, dropout=0.1
    )
    path = Path(__file__).resolve().parent.parent.parent / 'model' / 'transformer.pth'
    model.load_state_dict(torch.load(path, map_location=device))
    model.to(device)
    model.eval()

    # Tokenize input text
    encoding = tokenizer(text, max_length=MAX_LENGTH, padding='max_length', truncation=True, return_tensors='pt')
    input_ids = encoding['input_ids'].to(device)
    attention_mask = encoding['attention_mask'].to(device)

    # Initialize Grad-CAM
    grad_cam = LayerGradCam(model, model.transformer_encoder)

    # Get Grad-CAM attributions for AI-written class (0)
    attributions = grad_cam.attribute(
        input_ids,
        target=0,  # Target class (AI-written = 0, Human-written = 1)
        additional_forward_args=(attention_mask,),
    )

    # Process tokens and their scores
    tokens = tokenizer.convert_ids_to_tokens(input_ids[0])
    # Detach the tensor before converting to numpy
    token_scores = attributions[0].detach().cpu().numpy()[0]

    # Create result list with token-level scores
    results = []
    for token, score in zip(tokens, token_scores):
        if token not in ['[PAD]', '[CLS]', '[SEP]']:
            # Normalize score to probability range [0, 1]
            normalized_score = float((score - token_scores.min()) / (token_scores.max() - token_scores.min()))
            results.append(
                {
                    'token': token,
                    'ai_prob': normalized_score,  # Higher score means more likely to be AI-written
                    'is_special_token': token.startswith('[') and token.endswith(']'),
                }
            )

    return results
