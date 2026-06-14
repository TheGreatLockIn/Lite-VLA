# Requirements files

Install profiles for Lite-VLA Python dependencies.

| File | Profile |
|------|---------|
| `base.txt` | ML inference + utilities |
| `dev.txt` | Base + pytest + ruff (**default**) |
| `train.txt` | Base + LoRA fine-tuning |
| `deploy.txt` | Base + quantization / export |
| `all.txt` | Dev + train |

**Full breakdown of each package and its role in the project:** [`docs/requirements.md`](../docs/requirements.md)

**Recommended setup:** `./scripts/setup_python_env.sh` from the repo root.
