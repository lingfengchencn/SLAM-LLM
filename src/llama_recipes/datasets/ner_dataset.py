import torch
from torch.utils.data import Dataset
import whisper
import kaldiio
import copy
import numpy as np
from tqdm import tqdm

import logging
logger = logging.getLogger(__name__)

class NerDataset(Dataset):
    def __init__(self, dataset_config, model_config, tokenizer=None, split='train',):
        super().__init__()
        self.data_list = []
        self.label_list = []
        self.key_list = []
        self.key_name_dict={} # for debug

        if split == "train":
            pass

        elif split == "val":
            with open(dataset_config.dev_scp_file_path + "ner_english.info",'r') as f:
                for line in f:
                    line = line.strip().split('\t')
                    path=line[0]
                    self.data_list.append(path)

                    key= path.rsplit('/')[-1]
                    key = key.split('.')[0]  #'1012-133424-0005'
                    self.key_list.append(key)

                    self.label_list.append(line[1]) 

            with open(dataset_config.dev_scp_file_path + "person_list",'r') as f:
                for line in f:
                    line=line.strip().split(' ', 1)
                    key = line[0]
                    name_list = line[1]
                    name_list= name_list.replace(" ", "")
                    name_list = name_list.split('|')[:-1]
                    name_list= " ".join(name_list)

                    self.key_name_dict[key] = name_list


        elif split == "test":  # 3188  只有prev用这个 不用ground truth 用解码
            pass


        self.model_config = model_config
        self.dataset_config = dataset_config
        self.tokenizer = tokenizer
        self.IGNORE_INDEX = -100  # The default setting in CrossEntropyLoss
        self.prompt_template = self.dataset_config.prompt
        self.answer_template = "{}"
        self.fix_length_audio = dataset_config.get("fix_length_audio", -1)
        self.inference_mode = dataset_config.get("inference_mode", False)
        self.split = split


    def __getitem__(self, index):
        wav_path = self.data_list[index]
        audio_raw = whisper.load_audio(wav_path) #(234432,)

        target = self.label_list[index]
        key = self.key_list[index] #'1012-133424-0005'
        ocr = self.key_name_dict[key] #'PETER'

        if self.dataset_config.use_ocr == True:
            prompt = self.prompt_template.format(ocr)
        else:
            prompt = "USER: Transcribe speech to text. \n ASSISTANT:"

        prompt_ids = self.tokenizer.encode(prompt)
        prompt_length = len(prompt_ids)


        if self.model_config.encoder_name == "hubert" or self.model_config.encoder_name == "wavlm":
            audio_raw = torch.from_numpy(audio_raw).float()
            audio_raw = torch.nn.functional.layer_norm(audio_raw, audio_raw.shape)
            audio_mel = None
        elif self.model_config.encoder_name == "whisper" and self.model_config.encoder_path == "/nfs/maziyang.mzy/models/Whisper/large-v3.pt":
            audio_raw = whisper.pad_or_trim(audio_raw)  #torch.Size([480000])
            audio_mel = whisper.log_mel_spectrogram(audio_raw,128).permute(1, 0)   # 128
        elif self.model_config.encoder_name == "whisper":
            audio_raw = whisper.pad_or_trim(audio_raw)  #torch.Size([480000])
            audio_mel = whisper.log_mel_spectrogram(audio_raw).permute(1, 0)    #torch.Size([3000, 80])   torch.Size([648, 80])


        if self.model_config.encoder_name == "hubert" or self.model_config.encoder_name == "wavlm":
            audio_length = audio_raw.shape[0] // 320  # ad-hoc for hubert
        elif self.model_config.encoder_name == "whisper":
            audio_length = (audio_mel.shape[0] + 1) // 2  # ad-hoc for whisper for 2x downsample from mel to feats
        
        audio_length = audio_length // 5 # ad-hoc for 5x fc downsample
        if self.fix_length_audio > 0:  # -1
            audio_length = self.fix_length_audio  # q-former
        audio_pseudo = torch.full((audio_length,), -1) # placeholder

        if self.inference_mode:
            prompt_ids = torch.tensor(prompt_ids, dtype=torch.int64)
            example_ids = torch.cat((audio_pseudo, prompt_ids))  # [audio,prompt]
            example_mask = example_ids.ge(-1)  # [True,True]

            return {
                "input_ids": example_ids,
                "attention_mask": example_mask,
                'audio_mel': audio_mel,
                "audio": audio_raw,
                'audio_length': audio_length,
                'key': key,
                'target': target,
            }

        answer = self.answer_template.format(target)
        example = prompt + answer  # FIX(MZY): avoid putting a bos token before answer.
        example_ids = self.tokenizer.encode(example)  # [prompt,answer]
        example_ids.append(self.tokenizer.eos_token_id)  # [prompt,answer,eos]
        example_ids = torch.tensor(
            example_ids, dtype=torch.int64
        )
        example_ids = torch.cat((audio_pseudo, example_ids))  # [audio,prompt,answer,eos]

        labels_ids = copy.deepcopy(example_ids)  # [audio,prompt,answer,eos]
        labels_ids[:audio_length + prompt_length] = -1  # [-1,-1,answer,eos];
        example_mask = example_ids.ge(-1)  # FIX(GZF): [True,True,True,True]

        label_mask = labels_ids.ge(0)  # [False,False,True,True]
        example_ids[~example_mask] = 0  # [audio,prompt,answer,eos]
        labels_ids[~label_mask] = self.IGNORE_INDEX  # [-100,-100,answer,eos]

        return {
            "input_ids": example_ids,
            "labels": labels_ids,
            "attention_mask": example_mask,
            'audio_mel': audio_mel,
            "audio": audio_raw,
            'audio_length': audio_length,
        }             


    def collator(self, samples):
        assert samples is not None
        input_ids_max_length = max([s['input_ids'].shape[0] for s in samples])
        input_ids = torch.stack([self.pad(s['input_ids'], input_ids_max_length, self.tokenizer.pad_token_id)
                                 for s in samples])
        attention_mask = torch.stack([self.pad(s['attention_mask'], input_ids_max_length, False)
                                      for s in samples])
    
        if self.model_config.encoder_name == "whisper":
            audio_mel_max_length = max([s['audio_mel'].shape[0] for s in samples])
            audio_mel = torch.stack([self.pad(s['audio_mel'], audio_mel_max_length, 0)
                                    for s in samples])
            audio_mel_post_mask = torch.zeros(len(samples), (audio_mel_max_length + 1) // 2) # ad-hoc for whisper for 2x downsample from mel to feats
            for line, sample in enumerate(samples):
                audio_mel_post_mask[line, :(sample['audio_mel'].shape[0] + 1) // 2] = 1
            
            audio = None
            audio_mask = None

        elif self.model_config.encoder_name == "hubert" or self.model_config.encoder_name == "wavlm":
            audio_max_length = max([s['audio'].shape[0] for s in samples])
            audio = torch.stack([self.pad(s['audio'], audio_max_length, 0)
                                    for s in samples])
            audio_mask = torch.ones(len(samples), audio_max_length) # hubert 的 padding_mask 前面是0 后面是1 !!!
            for line, sample in enumerate(samples):
                audio_mask[line, :sample['audio'].shape[0]] = 0
            
            audio_mel = None
            audio_mel_post_mask = None
    

        modality_mask = torch.zeros_like(attention_mask)
        for line, sample in enumerate(samples):
            modality_mask[line, :sample['audio_length']] = 1

        if self.inference_mode:
            keys = [s['key'] for s in samples]
            targets = [s['target'] for s in samples]

            return {
                'input_ids': input_ids,
                'attention_mask': attention_mask,
                'audio_mel': audio_mel,
                'audio_mel_post_mask': audio_mel_post_mask,
                "audio": audio,
                "audio_mask": audio_mask,
                'modality_mask': modality_mask,
                'keys': keys,
                'targets': targets
            }

        labels = torch.stack([self.pad(s['labels'], input_ids_max_length, self.IGNORE_INDEX)
                              for s in samples])
        return {
            'input_ids': input_ids,
            'labels': labels,
            'attention_mask': attention_mask,
            'audio_mel': audio_mel,
            'audio_mel_post_mask': audio_mel_post_mask,
            "audio": audio,
            "audio_mask": audio_mask,
            'modality_mask': modality_mask
        }


    def pad(self, sequence, max_length, padding_idx=0):
        if isinstance(sequence, (int, list, tuple)):
            if len(sequence) < max_length:
                sequence = sequence + [padding_idx] * (max_length - len(sequence))
            else:
                sequence = sequence[:max_length]
        elif isinstance(sequence, torch.Tensor):
            if len(sequence) < max_length:
                sequence = torch.cat(
                    (sequence, torch.full(([max_length - len(sequence)] + list(sequence.size())[1:]), padding_idx)))
            else:
                sequence = sequence[:max_length]
        else:
            raise Exception("Type mismatch during padding!")
        return sequence


    def __len__(self):
        return len(self.data_list)

def get_audio_dataset(dataset_config, model_config, tokenizer, split):
    dataset = NerDataset(dataset_config, model_config, tokenizer, split)
    return dataset



   