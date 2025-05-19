import torch.nn as nn
from transformers import AutoTokenizer

# Initialize tokenizer
# TODO: use https://huggingface.co/FacebookAI/xlm-roberta-base
tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
MAX_LENGTH = 512  # Maximum sequence length


class TransformerClassifier(nn.Module):
    def __init__(self, vocab_size, d_model=256, nhead=8, num_layers=6, dim_feedforward=1024, dropout=0.1):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, d_model)
        self.pos_encoder = nn.Dropout(dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=dim_feedforward, dropout=dropout, batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        self.classifier = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 2),  # 2 classes: human/AI
        )

    def forward(self, input_ids, attention_mask):
        # Create padding mask
        padding_mask = attention_mask == 0

        # Embedding and positional encoding
        x = self.embedding(input_ids)
        x = self.pos_encoder(x)

        # Transformer encoder
        x = self.transformer_encoder(x, src_key_padding_mask=padding_mask)

        # Global average pooling
        x = x.mean(dim=1)

        # Classification head
        x = self.classifier(x)
        return x
