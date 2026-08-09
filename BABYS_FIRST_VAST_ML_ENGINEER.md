# Baby's First Vast.ai ML Engineer Runbook

> A beginner-friendly, operationally serious guide to renting a Vast.ai GPU box,
> turning it into a reproducible training machine, diagnosing memory failures, running
> jobs safely, and copying every valuable artifact home before the instance disappears.
>
> **Read this before provisioning or changing a remote training instance.**
>
> Last updated: 2026-07-26
>
> Known-good reference workload: Qwen3.5-4B QLoRA/PPO with a frozen Qwen3.5-4B
> reference model and an 8B embedding model on 2x NVIDIA H100 80 GB.

---

## 0. The 60-second version

If you remember nothing else, follow this order:

1. Rent hardware appropriate for the **architecture**, not merely enough advertised VRAM.
2. For Qwen3.5 hybrid linear-attention training, use **Hopper H100**, not B200, unless
   Blackwell support has been independently revalidated.
3. Request enough disk and host RAM. For the known 4B experiment, 300 GB disk is comfortable.
4. SSH in and read `/etc/vast-agents-guide.md` if the image provides it.
5. Run `nvidia-smi` and stop every preinstalled inference process before loading training models.
6. Copy the repository to `/workspace/<project>` without copying a local virtual environment.
7. Create a fresh venv and install a CUDA-compatible PyTorch build **before** compiled extensions.
8. For Qwen3.5, install FLA, TileLang, and `causal-conv1d` in the documented order.
9. Run imports, CUDA tensor tests, and a tiny real-model backward pass before a full job.
10. Put every long run under Supervisor with `autorestart=false` and proper process-group killing.
11. Monitor metrics, output lengths, KL/entropy/loss, and GPU memory—not just process liveness.
12. Before stopping/destroying the instance, rsync outputs home and verify SHA-256 checksums.

A process that says `RUNNING` is not necessarily learning. It may be compiling, deadlocked,
leaking memory, or collapsing. The logs and diagnostics decide whether the run is healthy.

---

## 1. Mental model: what you are actually renting

A Vast.ai instance is a remote container on somebody else's GPU host.

There are four separate things to keep straight:

1. **Local machine** — where the durable copy of the code and results should live.
2. **Vast host** — the physical machine with the GPUs.
3. **Container filesystem** — the environment visible after SSH. This may disappear.
4. **Workspace volume** — optional persistent storage mounted into the container.

`/workspace` is only persistent when Vast says it is backed by a volume. Its name alone does
not make it durable.

On a Vast base image, check:

```bash
vast-capabilities | jq '.instance.workspace_is_volume'
```

- `true`: `/workspace` is backed by a persistent host volume.
- `false`: recycling or destroying the instance erases it.

A normal **stop/start** usually preserves the container filesystem. A **recycle** or
**destroy** may erase it. Treat all remote storage as temporary until an off-box checksum
matches.

### The local/remote notation used below

Commands marked **LOCAL** run from this machine.

Commands marked **REMOTE** run after SSHing into the Vast instance.

Do not paste local paths into the remote shell or remote paths into the local shell.

---

## 2. Known-good hardware and software snapshot

This exact environment completed Qwen3.5 forward, generation, backward, LoRA checkpointing,
and MMD/PPO training correctly.

### Hardware

- 2x NVIDIA H100 80 GB HBM3
- Hopper compute capability 9.0
- Approximately 296 GB container disk
- CUDA toolkit 12.9
- Host NVIDIA driver 580.126.20

### Python environment

- Python 3.12.3
- `torch==2.13.0+cu129`
- `transformers==5.14.1`
- `accelerate==1.14.0`
- `peft==0.19.1`
- `trl==1.9.1`
- `bitsandbytes==0.50.0`
- `sentence-transformers==5.6.1`
- `datasets==5.0.0`
- `flash-linear-attention==0.5.1`
- `causal-conv1d==1.6.2.post1`
- `tilelang==0.1.12`
- `triton==3.7.1`
- `numpy==2.4.4`
- `scipy==1.18.0`
- `scikit-learn==1.9.0`

This is a reproducibility snapshot, not a claim that these must remain the newest versions.
Do not casually upgrade a working training environment in the middle of an experiment.

### Proven Qwen3.5 device division

- GPU 0: trainable 4-bit Qwen3.5 policy plus LoRA
- GPU 1: frozen 4-bit Qwen3.5 reference plus Nemotron 8B embedder

The corrected critic-free DFT validation used approximately:

- GPU 0: 24 GiB peak allocated, 28 GiB peak reserved
- GPU 1: 24 GiB peak allocated, 25 GiB peak reserved

Earlier defective critic/objective code reached roughly 75 GiB reserved on GPU 0. A large
memory footprint can be a software/objective problem, not a model-size requirement.

---

## 3. Choosing a Vast.ai offer

### 3.1 Choose the GPU architecture deliberately

The newest GPU is not automatically the easiest training GPU.

For ordinary dense transformer models, B200 may be excellent. For Qwen3.5's hybrid
linear-attention/Gated DeltaNet stack, the surrounding Triton and FLA kernels were much
more mature on Hopper when this runbook was written.

#### Qwen3.5 rule

Use **H100 80 GB** for Qwen3.5 training unless a small real backward-pass smoke test has
already proven the exact package versions on B200.

Do not conclude that a B200 is safe because:

- The model loads.
- A forward pass works.
- The GPU has 180 GB VRAM.
- Another standard-attention Qwen model trains.

The failed B200 experiment loaded successfully, reserved roughly 104 GB on one GPU and
60 GB on the other, then sat at 0% GPU utilization while the CPU remained active. A tiny
batch could complete, but the first step was extremely slow and behavior was unreliable.

That was a software/architecture maturity failure, not a shortage of VRAM.

### 3.2 Number and size of GPUs

For the known DFT 4B configuration, select:

- 2 GPUs
- H100 80 GB each
- Prefer NVLink/SXM connectivity when price and availability are sensible

Two GPUs are useful even when the trainable model fits on one. The second can hold:

- A frozen reference model
- Reward models
- Embedding models
- Verifiers

For a different experiment, first make a memory inventory. Do not assume that adding the
parameter counts tells you the peak memory.

### 3.3 Host RAM

Model loading and quantization can temporarily use far more CPU RAM than steady-state GPU
training.

Guidelines:

- 4B/8B experiments: prefer at least 64 GB host RAM.
- 27B QLoRA: prefer 128 GB or more.
- Very large model loading, optimizer offload, or multiple models: 256 GB may be prudent.

`bitsandbytes` can stage high-precision weights in CPU RAM before quantization. A 27B model
can briefly require approximately 60+ GB just for staged weights.

### 3.4 Disk

Disk must cover more than the final model:

- Base-model cache
- Reference-model cache (shared cached files still occupy disk once)
- Embedding/reward models
- Python venv and compiled extensions
- Datasets
- Checkpoints
- Failed-run archives
- Temporary files during download/install

Recommendations:

- 4B plus 8B reward/embed model: 200 GB minimum, 300 GB comfortable.
- 27B and multiple checkpoints: 400–600 GB is safer.

The known-good instance used about 55 GB after setup and initial outputs, but that is not a
safe disk allocation for a longer checkpoint-heavy run.

### 3.5 Host reliability and networking

Prefer offers with:

- High reliability score
- Good download bandwidth
- Adequate disk throughput
- Sufficient contract duration or on-demand availability
- SSH access through a mapped port

A cheaper unstable host can cost more after repeated setup and interrupted runs.

### 3.6 Image choice

A minimal CUDA/PyTorch image without a preloaded inference model is simplest.

The proven instance used Vast's `llama.cpp` CUDA 12.9 image. It worked, but it started a
preinstalled llama-server that occupied about 19 GB on **each** H100. If using that image,
stopping the server is mandatory before training.

Do not install an NVIDIA driver inside the container. The host injects the driver. Installing
`cuda`, `cuda-drivers`, `nvidia-driver-*`, or replacement `libcuda*` packages can break the
container's connection to the host kernel driver.

---

## 4. Connect from the local machine

Set temporary shell variables so every command uses one source of truth.

**LOCAL:**

```bash
export VAST_HOST='REPLACE_WITH_PUBLIC_IP'
export VAST_PORT='REPLACE_WITH_SSH_PORT'
export VAST_KEY="$HOME/.ssh/id_vast"
```

Connect:

```bash
ssh -i "$VAST_KEY" -p "$VAST_PORT" root@"$VAST_HOST"
```

First connection only, if needed:

```bash
ssh -o StrictHostKeyChecking=accept-new \
  -i "$VAST_KEY" -p "$VAST_PORT" root@"$VAST_HOST"
```

Avoid disabling host-key checking globally. If Vast reassigns the same IP/port and SSH warns
that the host key changed, inspect and remove only the stale entry:

```bash
ssh-keygen -R "[$VAST_HOST]:$VAST_PORT"
```

### Read the image's own operating guide

**REMOTE:**

```bash
if [ -f /etc/vast-agents-guide.md ]; then
  less /etc/vast-agents-guide.md
fi
```

This tells an agent about the container's service manager, persistence, CUDA inventory, and
image-specific daemons. Read it before changing services.

---

## 5. Inventory the instance before installing anything

**REMOTE:**

```bash
date
uname -a
python3 --version
free -h
df -h /
df -h /workspace
nvidia-smi
nvidia-smi topo -m
nvcc --version || true
```

On a Vast base image:

```bash
vast-capabilities | jq '{
  image: .image,
  workspace_is_volume: .instance.workspace_is_volume,
  cuda: .hardware.gpu.cuda,
  services: .services
}'
```

Record the results in the experiment notes. Future debugging is much easier when you know
which driver, toolkit, image, and GPU architecture produced a result.

### Verify PyTorch only after installing the intended venv

Do not confuse the system Python's packages with the project's venv.

Inside the activated project venv, run:

```bash
python - <<'PY'
import torch
print('torch:', torch.__version__)
print('torch CUDA build:', torch.version.cuda)
print('CUDA available:', torch.cuda.is_available())
print('GPU count:', torch.cuda.device_count())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), torch.cuda.get_device_capability(i))
x = torch.randn(2048, 2048, device='cuda:0')
print('tensor test:', x.square().mean().item())
PY
```

`nvidia-smi` working does not prove that the installed PyTorch wheel contains kernels for
the GPU architecture.

---

## 6. Clear hidden GPU consumers first

Before interpreting any OOM, inspect GPU processes.

**REMOTE:**

```bash
nvidia-smi
nvidia-smi --query-compute-apps=pid,process_name,used_memory \
  --format=csv,noheader
ps aux --sort=-rss | head -20
supervisorctl status 2>/dev/null || true
```

On the proven Vast llama.cpp image:

```bash
supervisorctl stop llama
```

Then verify:

```bash
nvidia-smi --query-gpu=index,memory.used,memory.total \
  --format=csv,noheader
```

Both GPUs should be close to 0 MiB before the training process starts.

### Why this mattered

The preinstalled `llama-server` process consumed approximately:

- GPU 0: 18.8 GB
- GPU 1: 19.5 GB

That made a configuration that otherwise fit appear to OOM. The correct response was not to
reduce the training batch blindly—it was to stop an unrelated service.

### Do not run inference and training simultaneously unless planned

A local API server, notebook kernel, forgotten test process, or stale distributed worker can
consume VRAM. If the experiment requires separate inference and training phases, make the
service transition explicit.

For this project, also avoid parallel inference calls to a single local llama-server; they can
deadlock. Sequential calls are safer unless the server was explicitly configured and tested
for concurrency.

---

## 7. Copy the project to the instance

Do not copy a virtual environment from one machine to another. Compiled wheels, interpreter
paths, and CUDA extensions are machine/environment specific.

**LOCAL:**

```bash
PROJECT="$HOME/dft-eval-harness"
REMOTE_PROJECT='/workspace/dft-eval-harness'

rsync -az --info=progress2 \
  --exclude '.venv' \
  --exclude '.venv312' \
  --exclude '__pycache__' \
  --exclude '.git/objects' \
  -e "ssh -i $VAST_KEY -p $VAST_PORT" \
  "$PROJECT/" root@"$VAST_HOST":"$REMOTE_PROJECT/"
```

If Git history is important, do not exclude `.git/objects`. For a simple code/data transfer,
excluding it can save time.

Verify remotely:

```bash
cd /workspace/dft-eval-harness
find . -maxdepth 2 -type f | sort | head -100
```

### Never transfer secrets into the repository

Keep API and Hugging Face tokens outside tracked files. Do not put a token directly in a
committed shell script.

---

## 8. Configure Hugging Face cache and authentication

Use one explicit cache location so model downloads do not scatter across the filesystem.

**REMOTE:**

```bash
mkdir -p /workspace/.hf_home
chmod 700 /workspace/.hf_home
export HF_HOME=/workspace/.hf_home
```

Authenticate interactively:

```bash
source /workspace/dft-eval-harness/.venv/bin/activate
hf auth login
```

Or place a token in a root-readable file without printing it into logs:

```bash
install -m 600 /dev/null /workspace/.hf_home/token
# Open an editor and paste the token; do not echo it into shared logs.
```

A launch script can then use:

```bash
export HF_HOME=/workspace/.hf_home
export HF_TOKEN="$(cat /workspace/.hf_home/token)"
```

Before a long run, verify access to every gated model. A 30-minute setup should not fail three
hours later because the embedder was gated.

---

## 9. Build a clean Python environment

### 9.1 General rule for compiled ML packages

Install in this order:

1. Python venv tooling
2. Correct CUDA-enabled PyTorch wheel
3. Build tools (`ninja`, `packaging`, `wheel`)
4. Pure-Python/core ML packages
5. CUDA extensions compiled against the installed torch

Build isolation can create a temporary environment with a different PyTorch/CUDA build. For
extensions such as `causal-conv1d`, that can produce a false CUDA mismatch. Install it with
`--no-build-isolation` after torch is present.

### 9.2 Known-good Qwen3.5/H100 setup

The maintained bootstrap script is:

```text
/home/admin/dft-eval-harness/setup_h100.sh
```

Copy the project first, then run remotely:

```bash
cd /workspace/dft-eval-harness
bash setup_h100.sh
```

The equivalent manual process is:

```bash
cd /workspace/dft-eval-harness
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel packaging ninja

python -m pip install \
  torch==2.13.0+cu129 \
  --index-url https://download.pytorch.org/whl/cu129

python -m pip install \
  transformers==5.14.1 \
  accelerate==1.14.0 \
  peft==0.19.1 \
  trl==1.9.1 \
  bitsandbytes==0.50.0 \
  sentence-transformers==5.6.1 \
  datasets==5.0.0 \
  openai numpy scipy scikit-learn tqdm

python -m pip install \
  flash-linear-attention==0.5.1 \
  tilelang==0.1.12

python -m pip install --no-build-isolation \
  causal-conv1d==1.6.2.post1
```

If torchvision or torchaudio are genuinely needed, install matching cu129 builds from the
same PyTorch index. Do not install them merely out of habit.

### 9.3 Verify imports

```bash
source /workspace/dft-eval-harness/.venv/bin/activate
python - <<'PY'
import importlib.metadata as metadata
import torch
import transformers
import bitsandbytes
import fla
import causal_conv1d
import tilelang

for package in [
    'torch', 'transformers', 'accelerate', 'peft', 'trl',
    'bitsandbytes', 'sentence-transformers', 'datasets',
    'flash-linear-attention', 'causal-conv1d', 'tilelang', 'triton'
]:
    print(f'{package}=={metadata.version(package)}')

assert torch.cuda.is_available()
print('CUDA build:', torch.version.cuda)
print('GPUs:', [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])
PY
```

`bitsandbytes` may print:

```text
No prebuilt binary for CUDA 12.9, loading CUDA 12.8 instead.
```

That warning was benign with `bitsandbytes==0.50.0` in the proven environment. Import and
actual 4-bit model loading must still be tested.

### 9.4 Freeze the environment

After it works:

```bash
python -m pip freeze > environment.known-good.freeze.txt
python - <<'PY' > environment.runtime.txt
import platform, torch
print('python', platform.python_version())
print('torch', torch.__version__)
print('torch_cuda', torch.version.cuda)
print('cuda_available', torch.cuda.is_available())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i), torch.cuda.get_device_capability(i))
PY
```

Copy these files home with the experiment results.

---

## 10. Qwen3.5-specific requirements

Qwen3.5 is not a conventional all-softmax-attention transformer. It includes hybrid recurrent/
linear-attention components. That changes both software dependencies and failure modes.

### 10.1 Required fast path

Use current enough Transformers plus:

- `flash-linear-attention`
- `causal-conv1d`
- TileLang on Hopper with modern Triton

Without the fast path, Transformers may use a fallback implementation that materializes huge
activations and is far slower or larger than expected.

### 10.2 Hopper correctness guard

With Triton 3.4 or newer, FLA explicitly rejects a known incorrect gated-delta backward path
on Hopper and asks for TileLang. This is a correctness guard, not an arbitrary dependency.
Install TileLang rather than bypassing the check.

Never disable a backend's correctness assertion merely to make training start.

### 10.3 `causal-conv1d` build-isolation trap

A normal command such as:

```bash
pip install causal-conv1d
```

may build in an isolated environment containing a different torch wheel. The resulting error
can claim that system CUDA and PyTorch CUDA do not match even though the project venv is
correct.

Use:

```bash
pip install --no-build-isolation causal-conv1d==1.6.2.post1
```

only after installing the intended torch build and build tools.

### 10.4 Blackwell/B200 warning

The B200 attempt showed:

- Very high VRAM reservation unrelated to model parameter size
- Long step-zero stalls
- 0% GPU utilization while CPU stayed busy
- Fragile Triton/FLA compile/autotune behavior
- Unreliable throughput even when a tiny smoke test completed

Allocator settings and disabled autotuning helped diagnosis but did not make the stack reliable
enough for the experiment. Moving to H100 immediately completed backward.

Do not substitute Qwen2.5 merely because it is easier to train if Qwen3.5 architecture is part
of the research question. Change the hardware/software stack before changing the target.

---

## 11. CUDA and PyTorch compatibility without folklore

### Driver versus toolkit

The NVIDIA driver comes from the host. The CUDA toolkit and PyTorch wheel live in the
container/venv.

Exact minor versions do not always have to match. A host driver that supports CUDA 13 can run
many CUDA 12.x wheels. Do not reinstall the host driver to make `12.9` visually match.

### Architecture matters

A wheel can install successfully but lack kernels for a new GPU architecture. Blackwell needs
new enough CUDA builds. This often manifests only on the first CUDA operation:

```text
no kernel image is available for execution on the device
```

Check:

```bash
python - <<'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_arch_list())
print(torch.cuda.get_device_capability())
PY
```

### PTX JIT caveat

Code shipped as PTX from a toolkit newer than the host driver's JIT compiler may fail with:

```text
CUDA_ERROR_UNSUPPORTED_PTX_VERSION
```

Prefer a known-compatible wheel or native-cubin extension build. Do not begin by replacing the
host driver from inside the container.

---

## 12. Understand where GPU memory goes

Model weights are only one component.

Peak VRAM can include:

1. Quantized base weights
2. LoRA parameters
3. Gradients
4. Adam optimizer moments
5. Activations saved for backward
6. Full-vocabulary logits
7. KV cache used during generation
8. Frozen reference/reward models
9. CUDA kernels and workspaces
10. PyTorch allocator reservations
11. Unrelated processes

### 12.1 Full-vocabulary logits are enormous

For a vocabulary near 248,000, batch 20, and 257 response predictor positions:

```text
20 × 257 × 248,000 × 2 bytes ≈ 2.55 GB
```

That is one BF16 logits tensor. Float32 doubles it. Log-softmax may allocate another tensor.
Projecting logits for the full prompt plus response can double it again.

Mitigations:

- Use model support such as `logits_to_keep` to project only response positions.
- Gather selected token log-probabilities before moving between GPUs.
- Do not transfer full vocabulary logits across devices.
- Keep full-vocabulary tensors in BF16/FP16; cast selected scalar/token statistics to FP32.
- Disable `use_cache` in training forwards.

### 12.2 A critic can secretly dominate memory

A value head may seem tiny, but backpropagating its loss through all hidden states can retain a
large graph and update the shared LoRA backbone. In the known DFT run:

- Random critic plus value loss: GPU 0 reserved approximately 75 GiB.
- Critic disabled: GPU 0 reserved approximately 28 GiB.

It also halved step time. Do not add a critic reflexively. Verify its initialization, reward
scale, gradient path, and memory impact.

### 12.3 Allocated versus reserved

PyTorch's allocator reserves blocks for reuse.

- **Allocated**: memory currently occupied by tensors.
- **Reserved**: memory owned by PyTorch, including currently unused cached blocks.
- **`nvidia-smi` used**: process/driver view, often close to reserved plus overhead.

Log both:

```python
for i in range(torch.cuda.device_count()):
    print(i,
          torch.cuda.max_memory_allocated(i) / 2**30,
          torch.cuda.max_memory_reserved(i) / 2**30)
```

If reserved is much larger than allocated and allocations fail despite apparent free memory,
fragmentation may be involved.

### 12.4 Allocator configuration

Set this **before Python imports torch**:

```bash
export PYTORCH_ALLOC_CONF='expandable_segments:True,roundup_power2_divisions:[32:256,64:128,256:64,>:32]'
export PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_ALLOC_CONF"
```

The first variable is used by newer torch; the second supports older naming. Native Linux is
the validated environment. `expandable_segments` may not work under some WSL arrangements.

### 12.5 Triton autotuning

For the proven Qwen3.5 setup:

```bash
export TRITON_DISABLE_AUTOTUNING=1
```

This avoids costly or hanging autotuning paths. It is not a universal performance setting;
reassess it for a different model/backend after correctness is established.

---

## 13. Build experiments as reproducible launch packages

Every experiment should contain at least:

```text
project/
├── README.md
├── requirements.txt or lock/freeze file
├── train.py
├── test_train.py
├── launch_smoke.sh
├── launch_validation.sh
├── launch_full.sh
├── data or data manifest
└── outputs/  (not committed)
```

A launch script should:

- Use `set -euo pipefail`.
- `cd` to an absolute project directory.
- Activate the exact venv.
- Set cache and allocator variables before Python starts.
- Write to a new descriptive output directory.
- Include all important hyperparameters explicitly.
- Avoid embedding tokens or passwords.
- Run Python in the foreground so Supervisor owns it.

Template:

```bash
#!/bin/bash
set -euo pipefail
cd /workspace/my-experiment
source .venv/bin/activate

export HF_HOME=/workspace/.hf_home
export HF_TOKEN="$(cat /workspace/.hf_home/token)"
export PYTORCH_ALLOC_CONF='expandable_segments:True,roundup_power2_divisions:[32:256,64:128,256:64,>:32]'
export PYTORCH_CUDA_ALLOC_CONF="$PYTORCH_ALLOC_CONF"
export TRITON_DISABLE_AUTOTUNING=1

exec python train.py \
  --model-name exact/model-id \
  --out-dir outputs/run_name \
  --seed 42
```

Use `exec` so signals from Supervisor reach Python directly.

### Record configuration from inside the program

At startup, save:

- Parsed arguments
- Model IDs and revisions
- Package versions
- Seed
- Data manifest/hash
- Git commit or source checksum
- GPU names and count
- Torch/CUDA versions
- Start timestamp

Without this, a checkpoint may be impossible to interpret later.

---

## 14. The smoke-test ladder

Never jump directly from package installation to an overnight run.

### Level 1: imports and CUDA tensor

Time: under a minute.

Proves:

- Correct interpreter
- Packages import
- PyTorch sees the GPU
- Basic CUDA kernel works

### Level 2: model loading

Load each model onto its intended GPU **sequentially**. Check `nvidia-smi` after each load.

Proves:

- Authentication
- Checkpoint compatibility
- Quantization path
- Device mapping
- Baseline weight memory

### Level 3: generation only

Generate two responses from the exact target architecture.

Proves:

- Chat template/tokenizer
- Attention backend
- EOS/padding handling
- KV cache/generation path

### Level 4: one real backward step

Use the real loss and trainable modules, not a toy linear layer.

Start with a small batch but the intended prompt/response lengths.

Proves:

- Backward backend correctness
- CUDA extension compatibility
- LoRA gradients
- Optimizer step
- Peak activation memory

### Level 5: target-batch three-step smoke

Use the intended batch size. Include checkpointing and evaluation.

A one-step pass can hide:

- Optimizer-state allocation on the first update
- Allocator growth
- Graph leaks
- Policy drift
- Compile warmup

Three steps reveal whether memory and time settle.

### Level 6: guarded short validation

Run 10–20 steps with frequent evaluation and automatic stop conditions.

Watch:

- KL or trust-region diagnostics
- Entropy
- Output token length
- EOS/truncation rate
- Reward variance
- Loss scale
- NaN/Inf
- Task metrics
- GPU peak allocated/reserved

### Level 7: full run

Only after every earlier level passes.

Do not resume a checkpoint created under a mathematically incorrect objective merely to save
setup time. Archive it, fix the objective, and restart from the pristine base.

---

## 15. Benchmark batch size scientifically

Do not select batch size from intuition alone.

For each candidate batch:

1. Start from the same base/model state.
2. Run at least 2–3 steady steps.
3. Record examples/second, step time, and peak allocated/reserved VRAM.
4. Leave a safety margin for evaluation, checkpoints, and allocator variability.

The original DFT critic-enabled benchmark found:

- Batch 16: roughly 80 seconds/step, 58.6 GiB peak allocated.
- Batch 20: roughly 83 seconds/step, 71.9 GiB allocated, 75 GiB reserved.

After correcting the objective and disabling the unnecessary critic:

- Batch 20: roughly 43 seconds/step, 24 GiB allocated, 28 GiB reserved.

This illustrates why code-path changes can matter more than reducing batch size.

Do not automatically raise batch to consume all newly free VRAM. Distributional objectives may
have statistical reasons for a larger rollout population, but generation, backward mini-batch,
and MMD population can be decoupled deliberately.

---

## 16. Run long jobs under Supervisor

SSH sessions disconnect. Shell background jobs are easy to lose. Use Supervisor.

### 16.1 Configuration template

**REMOTE:** create `/etc/supervisor/conf.d/my-training.conf`:

```ini
[program:my-training]
command=/workspace/my-experiment/launch_full.sh
directory=/workspace/my-experiment
autostart=false
autorestart=false
startsecs=1
stopasgroup=true
killasgroup=true
stdout_logfile=/tmp/my_training.log
stderr_logfile=/tmp/my_training.err
stdout_logfile_maxbytes=0
stderr_logfile_maxbytes=0
environment=PROC_NAME="my-training"
```

Why these settings:

- `autostart=false`: rebooting the container does not unexpectedly consume credits.
- `autorestart=false`: a bad objective or OOM does not loop forever.
- `stopasgroup=true` and `killasgroup=true`: stopping Supervisor kills child workers too.
- Unlimited log size is acceptable for a short experiment; use rotation for very long jobs.

Load and start:

```bash
supervisorctl reread
supervisorctl update
supervisorctl start my-training
supervisorctl status my-training
```

Stop immediately if needed:

```bash
supervisorctl stop my-training
```

### 16.2 Interpret Supervisor states correctly

- `RUNNING`: process exists. It may still be hung or unhealthy.
- `STOPPED`: intentionally not running.
- `EXITED`: process ended. This is expected for a completed one-shot job when
  `autorestart=false`; inspect exit logs and final artifacts.
- `FATAL`: repeated startup failure or bad configuration.

Completion requires all of:

- Expected final log message
- Exit without traceback
- Final checkpoint/summary present
- Metrics file parseable
- Artifacts copied off-box

### 16.3 Separate smoke and full services

Use distinct names and logs:

```text
dft-smoke
dft-validation
dft-full
```

Do not overwrite forensic logs from a failed run with a new launch.

---

## 17. Monitoring without disturbing training

Safe monitoring does not call the model. It reads process, logs, and device counters.

### Status and latest logs

```bash
supervisorctl status my-training
tail -50 /tmp/my_training.log
tail -50 /tmp/my_training.err
```

### GPU state

```bash
nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu,power.draw,temperature.gpu \
  --format=csv,noheader
```

### Process state

```bash
ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd --sort=-%cpu | head -30
```

### Disk

```bash
df -h /workspace
du -sh /workspace/my-experiment/outputs/* 2>/dev/null
```

### What healthy often looks like

- Step logs arrive at roughly consistent intervals after warmup.
- Peak reserved memory stabilizes.
- GPU utilization alternates appropriately when work is split between GPUs.
- Loss/reward diagnostics remain finite.
- Output length and entropy do not run away.
- Checkpoints and evaluations appear on schedule.

One GPU showing 0% in a single snapshot can be normal if the other GPU is embedding/scoring.
Repeated 0% on every GPU with no new logs is not normal.

### Do not monitor by generating extra samples from the training model

Parallel inference can consume VRAM, change caches, compete for kernels, or deadlock a server.
Use saved periodic evaluation outputs or pause training deliberately.

---

## 18. OOM and hang decision tree

### Symptom A: OOM during model loading

Check in this order:

1. `nvidia-smi` for unrelated processes.
2. Whether 4-bit/8-bit quantization was actually enabled.
3. Whether passing `torch_dtype` defeated or altered the intended quantized load.
4. Device map—did every model land on GPU 0?
5. Host RAM—did CPU staging die before GPU placement?
6. Cache/download corruption.

For this project, do not force `torch_dtype` in `from_pretrained` when a
`BitsAndBytesConfig` controls 4-bit loading. Let the quantizer set the compute dtype.

### Symptom B: load succeeds, first training forward OOMs

Likely causes:

- Batch too large
- Prompt plus response length larger than expected
- Full-vocabulary logits for every prompt token
- Training KV cache accidentally enabled
- Slow fallback attention implementation
- Padding to a pathological maximum

Actions:

- Log actual tensor shapes.
- Set `use_cache=False` in loss/PPO forwards.
- Use response-only logits projection.
- Use length bucketing/dynamic batching.
- Verify the fast attention backend is active.
- Reduce batch only after inspecting the above.

### Symptom C: forward succeeds, backward OOMs

Likely causes:

- Saved activations
- Critic/value loss retaining the backbone graph
- Full-precision logits/log-softmax
- Too many PPO epochs or retained graphs
- Optimizer state allocated on first step
- Accidental gradients through frozen models

Actions:

- Confirm reference/reward models have `requires_grad=False` and are under `no_grad`.
- Inspect which losses backpropagate through the policy backbone.
- Cast only selected-token statistics to FP32.
- Zero or remove unnecessary critic paths.
- Use gradient checkpointing only after verifying backend compatibility and performance.
- Reduce backward mini-batch separately from rollout batch.

### Symptom D: huge VRAM, 0% GPU, high CPU, no traceback

Possible causes:

- Triton compilation/autotuning
- A broken kernel compile
- Allocator fragmentation/retries
- CPU preprocessing/tokenization
- Network or filesystem waiting
- Deadlock

Actions:

```bash
nvidia-smi
ps -eo pid,stat,etime,%cpu,%mem,cmd --sort=-%cpu | head
ls -lt ~/.triton 2>/dev/null | head
```

Run a tiny exact-architecture backward smoke. A one-time compile can be acceptable; an
unbounded silent stall is not. For Qwen3.5 on B200, move to H100 rather than spending hours
trying random batch reductions.

### Symptom E: reserved memory grows each step

Possible causes:

- Graph/tensor references retained in metric dictionaries or lists
- `retain_graph=True`
- Outputs stored on GPU
- Variable shapes causing allocator fragmentation
- Evaluation mixed into training without cleanup

Actions:

- Store scalars with `.item()` and CPU arrays, not live GPU tensors.
- Delete full logits/outputs as soon as selected statistics are extracted.
- Use stable length buckets.
- Log allocated and reserved peaks every step.
- Reproduce in a 10-step memory-only smoke.

### Symptom F: process is alive but outputs collapse

This is not an OOM. Check:

- Entropy explosion or collapse
- Response token length
- EOS rate
- Non-English leakage
- KL sign and estimator definition
- Reward scale versus value/entropy losses
- Clipping fraction
- NaN/Inf

The failed DFT run remained technically healthy while output length fell from approximately
1,000 characters to 170 and entropy rose from 1 to 9. Supervisor could not detect this. Metric
guards and human interpretation stopped it.

---

## 19. Multi-GPU placement principles

Two GPUs do not automatically combine into one pool.

Decide explicitly which device owns each component:

```text
GPU 0: policy + LoRA + backward
GPU 1: frozen reference + embedder/reward model
```

### Avoid copying full logits between GPUs

A full `[batch, time, vocabulary]` tensor can be gigabytes. Compute selected token
log-probabilities on the source GPU and transfer only `[batch, response_time]`.

### Avoid accidental peer placement

After loading each model:

```python
print(next(policy.parameters()).device)
print(next(reference.parameters()).device)
print(embedder.device)
```

Also inspect `hf_device_map` where applicable.

### Pipeline utilization can alternate

GPU 0 may be idle while GPU 1 embeds responses. GPU 1 may be idle during policy backward. A
single utilization snapshot is not enough to diagnose underuse.

### Do not launch parallel model API calls casually

Parallel calls can deadlock local inference servers or cause memory spikes. Serial evaluation
is slower but safer until concurrency has been deliberately configured and tested.

---

## 20. Training-objective safety checks

Infrastructure success is not experiment success.

Every RL/on-policy run should log and guard at least:

- Reward mean and standard deviation
- Policy loss
- Value loss, if any
- Entropy
- Reference KL or another trust-region metric
- PPO old/new KL
- Clip fraction
- Average and median response tokens
- EOS rate
- Truncation rate
- Domain correctness/quality metric
- GPU peak allocated/reserved

### Beware fake or misused KL terms

A signed sampled log-ratio is not automatically a nonnegative differentiable KL loss.
Directly minimizing `new_log_prob - reference_log_prob` on fixed sampled tokens lowers the
probability of those tokens and can cause entropy explosion.

Standard PPO-style reference regularization commonly applies a detached rollout reward:

```text
-beta * (old_policy_logprob - reference_logprob)
```

Then PPO optimizes the resulting reward. Use a separately defined nonnegative estimator for
diagnostics.

### Reward-scale check

Print the relative sizes of every loss component. In the failed run:

- Witness reward standard deviation was around 0.02.
- Entropy coefficient contributed a larger pressure.
- Random critic value loss began near 2.67.

The intended reward was not the dominant learning signal.

### Automatic guards

For a new run, add stop conditions for:

- Any NaN/Inf
- Response length below a fraction of the initial baseline for multiple steps
- Entropy moving far beyond baseline
- Excessive reference KL
- Repeated domain-metric deterioration

A guard should save a report and stop cleanly without labeling the adapter `final`.

---

## 21. Preserve artifacts before rerunning or destroying

### 21.1 Archive failed runs; do not overwrite them

A failed checkpoint can reveal exactly when collapse began.

Use descriptive names:

```bash
mv outputs/current \
   outputs/failed_bad_kl_entropy_20260726
```

Preserve:

- Checkpoints
- stdout/stderr
- Per-step metrics
- Eval metrics
- Parsed configuration
- Source code used for the run
- Environment freeze
- Failure note

### 21.2 Sync home with resumable rsync

**LOCAL:**

```bash
mkdir -p "$HOME/experiment-archives/run_name"
rsync -az --partial --info=progress2 \
  -e "ssh -i $VAST_KEY -p $VAST_PORT" \
  root@"$VAST_HOST":/workspace/my-experiment/outputs/run_name/ \
  "$HOME/experiment-archives/run_name/"
```

Copy logs outside the output directory too:

```bash
scp -i "$VAST_KEY" -P "$VAST_PORT" \
  root@"$VAST_HOST":/tmp/my_training.log \
  "$HOME/experiment-archives/run_name/"

scp -i "$VAST_KEY" -P "$VAST_PORT" \
  root@"$VAST_HOST":/tmp/my_training.err \
  "$HOME/experiment-archives/run_name/"
```

### 21.3 Verify checksums

**REMOTE:**

```bash
sha256sum /workspace/my-experiment/outputs/run_name/checkpoint-*/adapter_model.safetensors
```

**LOCAL:**

```bash
sha256sum "$HOME"/experiment-archives/run_name/checkpoint-*/adapter_model.safetensors
```

Compare exact hashes. File sizes alone are not sufficient.

Create a manifest:

```bash
find "$HOME/experiment-archives/run_name" -type f -print0 \
  | sort -z \
  | xargs -0 sha256sum \
  > "$HOME/experiment-archives/run_name/SHA256SUMS"
```

### 21.4 Do not destroy immediately after transfer

Recommended order:

1. Stop training service.
2. Sync artifacts.
3. Verify checksums.
4. Open/parse summary and metrics locally.
5. Confirm final adapter exists.
6. Stop the Vast instance to halt GPU charges.
7. Destroy only after the local archive is proven complete.

Storage charges may continue while stopped, but that is cheaper than discovering a missing
checkpoint after destruction.

---

## 22. Starting a fresh run after a failed run

Use this procedure:

1. Stop the Supervisor service.
2. Verify no worker children remain.
3. Copy failed artifacts home.
4. Compare checksums.
5. Rename the remote output directory descriptively.
6. Fix code and add a regression test for the discovered failure.
7. Sync corrected code to the instance.
8. Run pure unit/syntax tests both locally and remotely.
9. Run a three-step real-model smoke from the pristine base.
10. Run a guarded 10–20-step validation from the pristine base.
11. Only then start the full run.

Do not continue from a checkpoint trained under a broken objective. It confounds the corrected
experiment and may preserve hidden damage even when sample outputs still look normal.

---

## 23. Teardown checklist

Before stopping/destroying:

```text
[ ] Training service stopped or completed
[ ] Final checkpoint exists
[ ] Intermediate best checkpoint exists
[ ] Metrics and summary copied locally
[ ] stdout/stderr copied locally
[ ] Launch scripts copied locally
[ ] Exact training source copied locally
[ ] Environment freeze copied locally
[ ] Data manifest/hash copied locally
[ ] Remote and local checkpoint SHA-256 match
[ ] Local summary JSON parses
[ ] Important adapter can be loaded locally or on another test machine
[ ] Vast instance stopped before eventual destruction
```

If any box is unchecked, the experiment is not safely preserved.

---

## 24. Generic first-run checklist for future agents

### Provisioning

```text
[ ] Target model architecture identified
[ ] GPU architecture known compatible with its kernels
[ ] Enough GPU VRAM
[ ] Enough host RAM for model staging
[ ] Enough disk for caches and checkpoints
[ ] Reliability/network acceptable
[ ] Persistence status understood
```

### Remote setup

```text
[ ] Read /etc/vast-agents-guide.md
[ ] Recorded GPU/driver/CUDA/image details
[ ] Stopped unrelated GPU services
[ ] Verified GPUs near 0 MiB before loading
[ ] Copied project without local venv
[ ] Configured HF_HOME and authentication
[ ] Installed torch before CUDA extensions
[ ] Frozen known-good package versions
```

### Validation

```text
[ ] Imports pass
[ ] CUDA tensor test passes
[ ] Models load on intended devices
[ ] Generation works
[ ] One exact backward step works
[ ] Target-batch three-step smoke stable
[ ] Short guarded validation stable
[ ] Output behavior remains sane
```

### Full run

```text
[ ] Supervisor service uses autorestart=false
[ ] Output directory is new and descriptive
[ ] Logs have dedicated paths
[ ] Checkpoints/evals scheduled
[ ] Collapse/OOM guards enabled
[ ] Off-box sync plan ready
```

---

## 25. Known project files on the local machine

For the DFT/Qwen3.5 experiment, consult:

- `/home/admin/dft-eval-harness/DFT_RESEARCH_DOSSIER.md`
- `/home/admin/dft-eval-harness/B200_QWEN35_TRAINING_TROUBLESHOOTING.md`
- `/home/admin/dft-eval-harness/setup_h100.sh`
- `/home/admin/dft-eval-harness/launch_validation_h100.sh`
- `/home/admin/dft-eval-harness/train_dft.py`
- `/home/admin/dft-eval-harness/test_train_dft.py`

The research dossier explains the algorithm. This runbook explains how to make the remote
machine reliably execute experiments.

---

## 26. How to solve problems this runbook does not cover

A runbook cannot anticipate every GPU, model architecture, compiler, package release, or
training objective. When a new failure appears, do not begin with random commands. Use a
repeatable investigation process.

### 26.1 First decide whether to stop the run

Stop immediately when continuing can:

- Corrupt or overwrite the only checkpoint
- Spend substantial credits without producing useful evidence
- Train under a mathematically invalid objective
- Produce escalating NaN/Inf, entropy, KL, or memory
- Damage data or delete remote artifacts
- Leak a credential

Keep the process running briefly only when its live state is necessary for inspection and the
cost/risk is low. Taking `nvidia-smi`, process, stack, and log snapshots before stopping can be
valuable.

Prefer reversible actions:

- Stop a Supervisor process rather than killing the whole instance.
- Rename an output directory rather than deleting it.
- Copy logs/checkpoints home before editing in place.
- Create a new launch script rather than overwriting the known-good one.

Ask the user before irreversible or materially expensive actions such as destroying an
instance, changing the target architecture, abandoning a major experiment premise, or
launching a large scale-up. Safe diagnostics and small reversible smoke tests can usually be
performed autonomously.

### 26.2 Write the problem in one falsifiable sentence

Bad problem statement:

```text
Training is broken.
```

Useful problem statement:

```text
On 2x B200, Qwen3.5-4B reaches epoch start, reserves 104/60 GB, then emits no
step log for 10 minutes while both GPUs remain at 0% and the process uses 230% CPU.
```

Include:

- Exact expected behavior
- Exact observed behavior
- The first stage where they differ
- Time scale
- Hardware/software versions
- Whether the issue reproduces

A precise symptom prevents unrelated fixes from becoming attractive.

### 26.3 Separate observation, inference, and decision

Keep these categories distinct:

```text
Observation: PID 688 uses 18.8 GB on GPU 0 and 19.5 GB on GPU 1.
Inference: an unrelated inference server is consuming training headroom.
Decision: stop Supervisor service `llama` and rerun the identical smoke test.
```

Do not write an inference as though it were observed fact. For example, 0% GPU utilization is
an observation; “Triton is deadlocked” is a hypothesis until tested.

### 26.4 Locate the failing layer

Classify the problem before changing anything:

1. **Instance layer** — hardware, disk, network, credits, persistence
2. **Service layer** — hidden processes, Supervisor, ports, stale workers
3. **Environment layer** — Python, torch, CUDA, driver, compiled packages
4. **Data layer** — malformed examples, token lengths, corruption, leakage
5. **Model-load layer** — authentication, quantization, device mapping
6. **Forward/generation layer** — tokenizer, masks, cache, attention backend
7. **Backward/optimizer layer** — gradients, activation memory, extension correctness
8. **Objective layer** — reward signs, scales, KL, critic, clipping
9. **Evaluation layer** — slicing, references, sample size, judge bias
10. **Artifact layer** — checkpoint save/load, sync, checksum, resume semantics

Test the boundary immediately before and after the suspected layer. If imports and CUDA tensors
work but model load fails, do not debug PPO. If forward works but exact backward fails, do not
change the dataset first.

### 26.5 Preserve a diagnostic snapshot

Before restarting or editing, capture:

```bash
date
supervisorctl status 2>/dev/null || true
nvidia-smi
ps -eo pid,ppid,stat,etime,%cpu,%mem,cmd --sort=-%cpu | head -50
free -h
df -h /workspace
tail -200 /tmp/the_run.log
tail -200 /tmp/the_run.err
```

Also save:

- Parsed run configuration
- Last healthy and first unhealthy metric rows
- Package versions
- Source file checksum
- Checkpoint listing and sizes
- Exact exception text, including the first traceback, not merely the final wrapper error

Do not rerun until the evidence needed to compare old and new behavior is preserved.

### 26.6 Reduce to the smallest faithful reproducer

“Small” is not enough; it must still execute the failing path.

Examples:

- An import test diagnoses binary compatibility but not backward kernels.
- A forward pass does not test gated-delta backward.
- Batch 1 may not exercise an MMD population objective.
- A toy transformer does not reproduce Qwen3.5's hybrid attention.
- A different model family may avoid the bug rather than explain it.

Reduce one dimension at a time:

1. Same target model and backend
2. Same failing operation
3. Fewer examples
4. Shorter sequence if sequence length is not the suspected cause
5. One optimizer step
6. Minimal evaluation/checkpointing

A faithful three-step smoke test is often more informative than hours of full training.

### 26.7 Rank hypotheses before testing them

Create a short table:

| Rank | Hypothesis | Evidence for | Evidence against | Cheapest falsifying test |
|---:|---|---|---|---|
| 1 | Hidden GPU process | Baseline VRAM already occupied | None yet | `nvidia-smi` process list |
| 2 | Full-logit memory | Peak occurs at LM head | Model is only 4B | Log tensor shapes/use response-only logits |
| 3 | Allocator fragmentation | Reserved far above allocated | Fresh process also fails | Fresh tiny run with allocator config |

Rank by:

- Fit to the exact symptom
- Prior probability
- Cost of testing
- Risk of the test
- Ability to distinguish competing explanations

Test the cheapest high-information hypothesis first. Do not start by reinstalling the entire
machine.

### 26.8 Change one meaningful variable at a time

If you simultaneously:

- Change GPU architecture
- Upgrade torch
- Lower batch size
- Enable checkpointing
- Switch model family

then a successful run teaches almost nothing about the cause.

Keep a control configuration and record each delta. When several changes are inseparable, say
so explicitly and plan follow-up ablations.

Use new output directories for every diagnostic run. Never let two tests write the same metrics
or checkpoint path.

### 26.9 Instrument the boundary, not everything indiscriminately

Add measurements where information crosses the suspected boundary:

- Before/after each model load: GPU memory and device map
- Before/after generation: input width, output width, EOS, cache
- Before/after forward: logits shape/dtype
- Before/after backward: allocated/reserved peaks and gradient norm
- Before/after optimizer step: old/new KL and parameter delta
- Before/after evaluation decoding: padded width and response-only slice

Excessive logging can slow or perturb training. Log scalars, shapes, dtypes, and selected
samples rather than full tensors.

### 26.10 Read source and primary evidence

When an error is unfamiliar:

1. Search the exact quoted error.
2. Add model name, GPU architecture, torch, Triton, or extension name.
3. Prefer official documentation, source code, release notes, and maintainer issue threads.
4. Check issue dates and package versions.
5. Read the code that raises a correctness guard before bypassing it.
6. Distinguish exact matches from merely similar symptoms.

A report on AMD may reveal a Triton-autotune failure pattern relevant to Blackwell, but it is
not proof of the same root cause. Use analogous reports to generate hypotheses, then verify on
the actual stack.

Never disable a warning or assertion solely because a search result says it is safe. Determine
what invariant the check protects.

### 26.11 Use decision thresholds and timeboxes

Define in advance what counts as success or pivot:

```text
If the exact one-step backward does not finish within five minutes on H100, stop.
If reference KL exceeds 0.02/token, save a guard report and stop.
If output length remains below 60% of baseline for two rollouts, stop.
If the same B200 kernel stall survives one allocator and one backend test, move to H100.
```

Timeboxes prevent random-walk debugging. A reasonable sequence is:

- Minutes: hidden processes, disk, authentication, obvious configuration
- 15–30 minutes: minimal reproducer and instrumentation
- 30–90 minutes: package/backend compatibility research
- Longer: only with a strong hypothesis and evidence that the answer matters

A pivot is rational when it preserves the scientific target while replacing an unreliable
implementation layer. Moving Qwen3.5 from B200 to H100 did this. Switching from Qwen3.5 to
Qwen2.5 would have changed the target architecture and therefore the experiment.

### 26.12 Distinguish workaround from root cause

Examples:

- Lowering batch size may avoid an OOM without explaining it.
- Restarting may clear fragmentation without identifying the retained tensor.
- Disabling a critic may fix memory and objective stability, but the root causes are its graph
  path, initialization, and loss scale.
- Moving to H100 works around Blackwell kernel immaturity; it does not prove B200 hardware is
  defective.

Document both:

```text
Root cause: sampled log-ratio was used as a differentiable KL loss on fixed actions.
Immediate workaround: stop the collapsing run.
Correct fix: move KL into detached rollout reward and add proper diagnostics/tests.
```

This prevents future agents from cargo-culting a workaround into unrelated experiments.

### 26.13 Turn every solved failure into infrastructure

After identifying a cause:

1. Add a focused regression test.
2. Add a startup assertion if the invalid state can be detected cheaply.
3. Add a runtime guard if it can emerge later.
4. Correct the bootstrap/launch script.
5. Update this runbook or the project-specific dossier.
6. Preserve a failed-run manifest showing the signature.

A debugging session is incomplete if the next fresh instance can repeat the same failure
silently.

### 26.14 Report a situation clearly

A useful status report has five parts:

1. **State** — running, stopped, completed, guarded, or failed
2. **Evidence** — step, metrics, memory, exact error
3. **Interpretation** — what the evidence supports and what remains uncertain
4. **Action taken** — especially anything stopped, archived, or launched
5. **Next decision point** — acceptance threshold and expected time

Template:

```text
State: stopped at step 53.
Evidence: entropy 1→9, output length 1,000→170 chars, MMD worsened, signed KL -0.8.
Interpretation: objective-driven policy collapse, not hardware OOM.
Action: stopped Supervisor and copied checkpoints 20/40 home with matching SHA-256.
Next: correct KL/critic/entropy paths, pass three-step smoke, then run 20-step validation.
```

Do not call noisy early metrics a win. Separate “stable enough to continue” from “scientifically
proven improvement.”

### 26.15 General investigation worksheet

Copy this into the experiment notes:

```text
Goal:
Expected behavior:
Observed behavior:
First failing stage:
Last known-good configuration:
Hardware/image:
Python/torch/CUDA/backend versions:
Artifacts at risk:
Immediate stop required? Why?:

Observations:
1.
2.
3.

Ranked hypotheses:
1. Hypothesis — falsifying test — result
2. Hypothesis — falsifying test — result
3. Hypothesis — falsifying test — result

Single variable changed:
Control result:
Treatment result:
Conclusion confidence:
Workaround:
Root-cause fix:
Regression test/guard added:
Artifacts synced and checksummed:
Next decision threshold:
```

This process applies beyond ML training—to deployment, inference, networking, data pipelines,
and evaluation. The technical commands change; the discipline does not.

---

## 27. Final principles

1. **Architecture compatibility beats advertised VRAM.**
2. **Clear unrelated GPU processes before reducing the experiment.**
3. **Install torch first, then compile extensions against that torch.**
4. **Prove the exact backward path, not merely model loading.**
5. **Separate rollout population, backward mini-batch, and reference batch deliberately.**
6. **Log tensor/memory/objective diagnostics, not just loss.**
7. **A live process can still be a failed experiment.**
8. **Archive failed runs—they are evidence.**
9. **Supervisor protects against SSH loss; guards protect against silent collapse.**
10. **State observations separately from inferences and decisions.**
11. **Test ranked hypotheses with the smallest faithful reproducer.**
12. **Change one meaningful variable at a time.**
13. **Turn every root cause into a test, guard, script fix, or runbook update.**
14. **Nothing on rented hardware is real until a verified copy exists at home.**
