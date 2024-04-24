#!/bin/bash
#export PYTHONPATH=/root/whisper:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=2
# export CUDA_LAUNCH_BLOCKING=1

cd /root/SLAM-LLM

# speech_encoder_path= ???

# llm_path=/nfs/zhifu.gzf/ckpt/Llama-2-7b-hf
# llm_path=/nfs/maziyang.mzy/models/Llama-2-7b-chat-hf
llm_path=/nfs/maziyang.mzy/models/vicuna-7b-v1.5


output_dir=/nfs/yangguanrou.ygr/vicuna-7b-v1.5-finetune-sota-vsr-20230119
# ckpt_path=$output_dir/avsr/3
ckpt_path=$output_dir/avsr/27
# peft_ckpt=/nfs/maziyang.mzy/exps/llama-2-hf-finetune-asr-ds5-proj2048-lr1e-4-whisper-lora-prompt-paddinglr-20240102/asr/4
# val_data_path= ??
decode_log=$ckpt_path/decode_log_test_other_beam4_repetition_penalty1

# -m debugpy --listen 5678 --wait-for-client
python src/llama_recipes/pipeline/inference_batch.py \
--model_name avsr \
--freeze_encoder \
--llm_name vicuna-7b-v1.5 \
--llm_path $llm_path \
--llm_dim 4096 \
--encoder_name sota_avsr \
--encoder_dim 768 \
--encoder_projector linear \
--encoder_projector_ds_rate 5 \
--dataset avsr_dataset \
--avsr_dataset.file src/llama_recipes/datasets/avsr_dataset_inference.py:get_audio_dataset \
--batching_strategy custom \
--num_epochs 1 \
--val_batch_size 1 \
--num_workers_dataloader 0 \
--output_dir $output_dir \
--ckpt_path $ckpt_path/model.pt \
--decode_log $decode_log \
--freeze_llm \
--test_split test \
--modality "visual" \
--pretrained_model_path "/nfs/yangguanrou.ygr/auto_avsr/vsr_trlrwlrs2lrs3vox2avsp_base.pth" \


# --peft_ckpt $peft_ckpt \
# --use_peft --peft_method lora \
# --speech_dataset.val_data_path $val_data_path \