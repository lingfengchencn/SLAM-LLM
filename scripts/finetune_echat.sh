#!/bin/bash
#export PYTHONPATH=/root/whisper:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0,1
export CUDA_LAUNCH_BLOCKING=1
# export OMP_NUM_THREADS=1
# export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

# debug setting for multiple gpus
# export NCCL_DEBUG=INFO
# export NCCL_DEBUG_SUBSYS=ALL
# export TORCH_DISTRIBUTED_DEBUG=INFO

cd /root/SLAM-LLM

# speech_encoder_path=/nfs/zhifu.gzf/ckpt/Whisper/large-v2.pt
speech_encoder_path=/nfs/maziyang.mzy/models/Whisper/large-v2-qwen.pt
llm_path=/nfs/zhifu.gzf/ckpt/Llama-2-7b-hf
output_dir=/nfs/maziyang.mzy/models/llama-2-hf-proj2048-debug

# -m debugpy --listen 5678 --wait-for-client
if [[ $CUDA_VISIBLE_DEVICES != *","* ]]; then
python -m debugpy --listen 5678 --wait-for-client src/llama_recipes/pipeline/finetune.py \
--model_name echat \
--freeze_encoder \
--freeze_llm \
--use_fp16 \
--llm_name llama-2-7b-hf \
--llm_path $llm_path \
--encoder_name whisper \
--encoder_ds_rate 2 \
--encoder_path $speech_encoder_path \
--encoder_projector linear \
--encoder_projector_ds_rate 5 \
--dataset custom_dataset \
--custom_dataset.file src/llama_recipes/datasets/echat_dataset.py:get_audio_dataset \
--custom_dataset.data_path /nfs/zhifu.gzf/data/IEMOCAP_full_release/datalist.jsonl \
--batching_strategy custom \
--custom_dataset.max_words 1024 \
--num_epochs 100 \
--batch_size_training 2 \
--val_batch_size 2 \
--output_dir $output_dir \
--run_test_during_validation \
--run_test_during_validation_file /nfs/zhifu.gzf/data/IEMOCAP_full_release/Session5/sentences/wav/Ses05M_impro04/Ses05M_impro04_M040.wav \
# --ckpt_path "/nfs/maziyang.mzy/models/llama-2-hf-finetune/echat/1/model.pt" \
# --peft_ckpt "/nfs/maziyang.mzy/models/llama-2-hf-finetune/echat/1" 
# --use_peft --peft_method lora \

# train
# {"trans": "Well, do you have your passport?\n", 
# "emotion": "xxx",
# "wav": "/nfs/zhifu.gzf/data/IEMOCAP_full_release/Session1/sentences/wav/Ses01M_impro01/Ses01M_impro01_F009.wav"}
# {"trans": "No, I don't have a passport.\n", 
# "emotion": "neu", 
# "wav": "/nfs/zhifu.gzf/data/IEMOCAP_full_release/Session1/sentences/wav/Ses01M_impro01/Ses01M_impro01_M010.wav"}

# val
# {"trans": "Yeah, well thanks for your help.\n",
# "emotion": "ang",
# "wav": "/nfs/zhifu.gzf/data/IEMOCAP_full_release/Session5/sentences/wav/Ses05M_impro04/Ses05M_impro04_M040.wav"}
# {"trans": "I'm sorry.  Good luck, man.\n",
# "emotion": "xxx", 
# "wav": "/nfs/zhifu.gzf/data/IEMOCAP_full_release/Session5/sentences/wav/Ses05M_impro04/Ses05M_impro04_F038.wav"}

else
torchrun \
--nnodes 1 \
--nproc_per_node 2 \
src/llama_recipes/pipeline/finetune.py \
--model_name echat \
--freeze_encoder \
--freeze_llm \
--use_fp16 \
--enable_fsdp --low_cpu_fsdp \
--llm_name llama-2-7b-hf \
--llm_path $llm_path \
--encoder_name whisper \
--encoder_ds_rate 2 \
--encoder_path $speech_encoder_path \
--encoder_projector linear \
--encoder_projector_ds_rate 5 \
--dataset custom_dataset \
--custom_dataset.file src/llama_recipes/datasets/echat_dataset.py:get_audio_dataset \
--custom_dataset.data_path /nfs/zhifu.gzf/data/IEMOCAP_full_release/datalist.jsonl \
--batching_strategy custom \
--custom_dataset.max_words 1024 \
--num_epochs 100 \
--batch_size_training 2 \
--val_batch_size 2 \
--output_dir $output_dir \
--run_test_during_validation \
--run_test_during_validation_file /nfs/zhifu.gzf/data/IEMOCAP_full_release/Session5/sentences/wav/Ses05M_impro04/Ses05M_impro04_M040.wav \
# --ckpt_path "/nfs/maziyang.mzy/models/llama-2-hf-finetune/echat/1/model.pt" \
# --peft_ckpt "/nfs/maziyang.mzy/models/llama-2-hf-finetune/echat/1" 
# --use_peft --peft_method lora \
fi
