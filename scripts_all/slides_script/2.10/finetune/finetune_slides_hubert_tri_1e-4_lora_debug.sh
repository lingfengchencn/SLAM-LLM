#!/bin/bash
export PYTHONPATH=/root/fairseq:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false
# export CUDA_LAUNCH_BLOCKING=1
export OMP_NUM_THREADS=1


export MASTER_ADDR=localhost # Or the actual IP if it's a remote cluster
export MASTER_PORT=12345 # A free port number
export WORLD_SIZE=1 # Assuming you have 4 GPUs
export RANK=0
export LOCAL_RANK=0
# export RANK=$OMPI_COMM_WORLD_RANK # If you are using OpenMPI
# # OR
# export RANK=$SLURM_PROCID # If you are running on a SLURM-managed cluster

cd /root/SLAM-LLM

speech_encoder_path=/nfs/yangguanrou.ygr/hubert_ckpt/hubert_xtralarge_ll60k_finetune_ls960.pt

llm_path=/nfs/maziyang.mzy/models/vicuna-7b-v1.5

output_dir=/nfs/yangguanrou.ygr/slides-finetune-hubert-tri-1e-4-lora-debug

python -m debugpy --listen 5679 --wait-for-client src/llama_recipes/pipeline/finetune.py \
--config-path "/root/SLAM-LLM/scripts/slides_conf" \
--config-name "slides.yaml" \
hydra.run.dir=$output_dir \
++model_config.llm_name="vicuna-7b-v1.5" \
++model_config.llm_path=$llm_path \
++model_config.llm_dim=4096 \
++model_config.encoder_name=hubert \
++model_config.encoder_path=$speech_encoder_path \
++model_config.encoder_dim=1280 \
++model_config.encoder_type="finetune" \
++encoder_projector=linear \
++encoder_projector_ds_rate=5 \
++dataset_config.dataset=slides_dataset \
++dataset_config.use_ocr=true \
++train_config.model_name=asr \
++train_config.freeze_encoder=true \
++train_config.freeze_llm=false \
++train_config.batching_strategy=custom \
++train_config.warmup_steps=1000 \
++train_config.total_steps=110000 \
++train_config.batch_size_training=6 \
++train_config.val_batch_size=6 \
++train_config.num_workers_dataloader=0 \
++train_config.lr=1e-4 \
++train_config.scheduler=tri \
++train_config.validation_interval=10 \
++train_config.output_dir=$output_dir \
++train_config.enable_fsdp=false \
++train_config.enable_ddp=true \
++train_config.use_fp16=true \
++train_config.use_peft=true \
++\metric=acc \
++log_config.log_file=/$output_dir/train.log \
++dataset_config.train_scp_file_path=/nfs/yangguanrou.ygr/slidespeech/train_debug/ \
++dataset_config.dev_scp_file_path=/nfs/yangguanrou.ygr/slidespeech/dev_debug/ \
# ++log_config.use_wandb=true \
# ++log_config.wandb_dir=$output_dir \
# ++log_config.wandb_entity_name=yanghaha \
# ++log_config.wandb_project_name=slam-llm-slides \
# ++log_config.wandb_exp_name=slides-finetune-hubert-tri-1e-4-lora \
# ++log_config.log_interval=10 \





# cd /root
# cp -r SLAM-LLM/ /nfs/yangguanrou.ygr/codes/