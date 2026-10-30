# Running DyslexiAdapt training on Windows or Google Colab (free tier)

The Claude sandbox cannot download model weights, so real training must run where huggingface.co is reachable.

## Google Colab (free)
    !git clone <your repo>  # or upload the repo zip and unzip
    %cd DyslexiAdapt_Autonomous_Claude_Master
    !pip install -q torch transformers scikit-learn pandas joblib
    !python -m ML.train_distilbert --csv DATA/gold.csv --manifest DATA/split_manifest.json --out artifacts/distilbert
Runtime -> Change runtime type -> GPU (T4) is faster but optional.

## Windows (PowerShell)
    py -m venv .venv ; .\.venv\Scripts\Activate.ps1
    pip install torch transformers scikit-learn pandas joblib
    python -m ML.train_distilbert --csv DATA\gold.csv --manifest DATA\split_manifest.json

## Pipeline smoke test (no download, never a result)
    python -m ML.train_distilbert --csv <any csv> --smoke

## If the weight download fails
`artifacts/distilbert/DOWNLOAD_FAILED.json` explains why and nothing is trained. Options: use a network that
reaches huggingface.co; download the model once and pass the folder with `--model <folder>`; use `--offline`
only when the model is already cached.

## Reading the output
`results.json` has `valid_for_scientific_claims`. It is true only when: research-valid human data +
frozen split manifest + pretrained weights actually loaded + not smoke mode.
