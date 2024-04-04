#!/bin/bash

export CUDA_VISIBLE_DEVICES=0
export TOKENIZERS_PARALLELISM=false
# export CUDA_LAUNCH_BLOCKING=1


cd /root/SLAM-LLM

speech_encoder_path=/nfs/maziyang.mzy/models/Whisper/large-v3.pt

llm_path=/nfs/maziyang.mzy/models/vicuna-7b-v1.5

output_dir=/nfs/yangguanrou.ygr/slides-finetune-whisperv3
ckpt_path=$output_dir/asr/9760
# peft_ckpt=/nfs/maziyang.mzy/exps/llama-2-hf-finetune-asr-ds5-proj2048-lr1e-4-whisper-lora-prompt-paddinglr-20240102/asr/4
val_data_path=/nfs/yangguanrou.ygr/slidespeech/test_oracle_v1/
decode_log=/root/SLAM-LLM/slides_script/3.1/whisper_decode_results/decode_test_whisper_1

# -m debugpy --listen 5678 --wait-for-client
python src/llama_recipes/pipeline/inference_batch_whisperv3.py \
--config-path "/root/SLAM-LLM/scripts/slides_conf" \
--config-name "slides.yaml" \
hydra.run.dir=$ckpt_path \
++model_config.llm_name="vicuna-7b-v1.5" \
++model_config.llm_path=$llm_path \
++model_config.llm_dim=4096 \
++model_config.encoder_name=whisper \
++model_config.encoder_ds_rate=2 \
++model_config.encoder_path=$speech_encoder_path \
++model_config.encoder_dim=1280 \
++model_config.encoder_projector=cov1d-linear \
++encoder_projector_ds_rate=5 \
++dataset_config.dataset=whisper_dataset \
++dataset_config.file=src/llama_recipes/datasets/whisper_dataset.py:get_audio_dataset \
++dataset_config.use_ocr=true \
++dataset_config.dev_scp_file_path=$val_data_path \
++dataset_config.inference_mode=true \
++train_config.model_name=asr \
++train_config.batching_strategy=custom \
++train_config.num_epochs=1 \
++train_config.val_batch_size=16 \
++train_config.num_workers_dataloader=1 \
++train_config.output_dir=$output_dir \
++ckpt_path=$ckpt_path/model.pt \
++decode_log=$decode_log \
++train_config.freeze_encoder=true \
++train_config.freeze_llm=true \