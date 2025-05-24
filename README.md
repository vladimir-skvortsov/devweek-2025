# devweek-2025

## Running the Application

This project consists of a frontend and backend service. You can run them separately or together using the provided shell script.

### Prerequisites

- Python 3.x
- Node.js and npm
- pip (Python package manager)

### Running the Services

Use the following commands to run the services:

```bash
# Run both frontend and backend services
./run.sh all

# Run only the backend service
./run.sh backend

# Run only the frontend service
./run.sh frontend

# Show help
./run.sh help
```

### Service Details

- **Backend**: FastAPI application running on `http://localhost:8000`
- **Frontend**: React application running on `http://localhost:3000`

### Development

The services are configured with hot-reload enabled, so any changes to the code will automatically restart the respective service.

## List of Used Datasets

### 1. Kaggle Datasets
1. **`sunilthite/llm-detect-ai-generated-text-dataset`**
   - File: `Training_Essay_Data.csv`
   - Description: AI-generated vs human-written essays
   - Columns: `text`, `generated` (0/1)

2. **`prajwaldongre/llm-detect-ai-generated-vs-student-generated-text`**
   - File: `LLM.csv`
   - Description: Student essays vs AI-generated text
   - Columns: `Text`, `Label` ('student'/'AI')

3. **`thedrcat/daigt-v4-train-dataset`**
   - Files: `daigt_magic_generations.csv`, `train_v4_drcat_01.csv`
   - Description: AI detection training data
   - Columns: `text`, `label` (0/1)

4. **`carlmcbrideellis/llm-7-prompt-training-dataset`**
   - Files:
     - `train_essays_RDizzl3_seven_v1.csv`
     - `train_essays_RDizzl3_seven_v2.csv`
     - `train_essays_7_prompts.csv`
     - `train_essays_7_prompts_v2.csv`
   - Description: Essay prompts and responses
   - Columns: `text`, `label` (0/1)

5. **`starblasters8/human-vs-llm-text-corpus`**
   - File: `data.csv`
   - Description: Human vs LLM text collection
   - Columns: `text`, `source` ('Human'/'LLM')

6. **Kaggle Competition: `llm-detect-ai-generated-text`**
   - File: `train_essays.csv`
   - Description: AI detection competition data
   - Columns: `text`, `generated` (0/1)

7. **`d0rj3228/russian-literature`**
   - Format: Text files
   - Description: Russian literary texts (human-only)
   - Columns: `text` (all marked human)

8. **`artalmaz31/complex-russian-dataset`**
   - Format: Text files
   - Description: Complex Russian texts (human-only)
   - Columns: `text` (all marked human)

9. **`mar1mba/russian-sentiment-dataset`**
   - File: `sentiment_dataset.csv`
   - Description: Russian sentiment analysis data
   - Columns: `text` (all marked human)

10. **`vsevolodbogodist/data-jokes`**
    - File: `dataset.csv`
    - Description: Russian jokes dataset
    - Columns: `text` (all marked human)

### 2. HuggingFace Datasets
11. **`shahxeebhassan/human_vs_ai_sentences`**
    - Description: Short human vs AI sentences
    - Columns: `text`, `label` (0=AI, 1=human)

12. **`ardavey/human-ai-generated-text`**
    - Description: Human vs AI text samples
    - Columns: `text`, `label` (0=AI, 1=human)

### 3. Local Datasets
13. **`raw/ruatd-2022-bi-train.csv`**
    - Description: Russian text authenticity dataset (train)
    - Columns: `Text`, `Class` ('H'=human)

14. **`raw/ruatd-2022-bi-val.csv`**
    - Description: Russian text authenticity dataset (validation)
    - Columns: `Text`, `Class` ('H'=human)

15. **`raw/generated.csv`**
    - Description: Mixed English/Russian generated content
    - Columns: `Text`, `is_human`, `language` ('en'/'ru')

### Final Dataset Composition
- Combined dataset removes duplicates based on `text` column
- Final structure:
  ```python
  ['id', 'text', 'is_human', 'lang']  # lang = 'en' or 'ru'