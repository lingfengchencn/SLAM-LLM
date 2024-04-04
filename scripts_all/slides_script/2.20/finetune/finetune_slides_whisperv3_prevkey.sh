#!/bin/bash
export PYTHONPATH=/root/fairseq:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0,1,2,3
export TOKENIZERS_PARALLELISM=false
# export CUDA_LAUNCH_BLOCKING=1
export OMP_NUM_THREADS=1

cd /root/SLAM-LLM

speech_encoder_path=/nfs/maziyang.mzy/models/Whisper/large-v3.pt

llm_path=/nfs/maziyang.mzy/models/vicuna-7b-v1.5

output_dir=/nfs/yangguanrou.ygr/slides-finetune-whisperv3_prevkey


torchrun \
--nnodes 1 \
--nproc_per_node 4 \
src/llama_recipes/pipeline/finetune.py \
--config-path "/root/SLAM-LLM/scripts/slides_conf" \
--config-name "slides.yaml" \
hydra.run.dir=$output_dir \
++model_config.llm_name="vicuna-7b-v1.5" \
++model_config.llm_path=$llm_path \
++model_config.llm_dim=4096 \
++model_config.encoder_name=whisper \
++model_config.encoder_ds_rate=2 \
++model_config.encoder_path=$speech_encoder_path \
++model_config.encoder_dim=1280 \
++model_config.encoder_projector=cov1d-linear \
++encoder_projector_ds_rate=5 \
++dataset_config.dataset=slides_dataset \
++dataset_config.task=context+keyword \
++dataset_config.prev_bar=2 \
++train_config.model_name=asr \
++train_config.freeze_encoder=true \
++train_config.freeze_llm=true \
++train_config.batching_strategy=custom \
++train_config.warmup_steps=1000 \
++train_config.total_steps=110000 \
++train_config.batch_size_training=4 \
++train_config.val_batch_size=4 \
++train_config.num_workers_dataloader=0 \
++train_config.lr=5e-5 \
++train_config.scheduler=tri \
++train_config.validation_interval=2000 \
++train_config.output_dir=$output_dir \
++train_config.enable_fsdp=false \
++train_config.enable_ddp=true \
++train_config.use_fp16=true \
++metric=acc \
++log_config.log_file=/$output_dir/train.log \
++log_config.use_wandb=true \
++log_config.wandb_dir=$output_dir \
++log_config.wandb_entity_name=yanghaha \
++log_config.wandb_project_name=slam-llm-slides \
++log_config.wandb_exp_name=slides-finetune-whisperv3_prevkey \
++log_config.log_interval=10 \





# cd /root
# cp -r SLAM-LLM/ /nfs/yangguanrou.ygr/codes/