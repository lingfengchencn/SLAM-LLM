import torch
from torch.utils.data import Dataset
import whisper
import kaldiio
import copy
import numpy as np
from tqdm import tqdm

import logging
logger = logging.getLogger(__name__)

class SlidesDataset(Dataset):
    def __init__(self, dataset_config, model_config, tokenizer=None, split='train',):
        super().__init__()
        self.dataset_config = dataset_config

        self.data_list = []
        self.num_samples_list = []
        self.label_list = []
        self.ocr_list = []
        self.name_list=[] # for debug

        if split == "train":
            # 一次性load 全部数据
            # logger.info("loading training audio data!")
            # scp_file = dataset_config.train_scp_file_path + "my_wav.scp" 
            # with kaldiio.ReadHelper('scp:'+ scp_file) as reader:
            #     for key, numpy_array in tqdm(reader):
            #         self.data_list.append( numpy_array[1].astype(np.float32) )
            # logger.info("Finish loading!")

            with open(dataset_config.train_scp_file_path + "my_wav.scp",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.data_list.append(line[1])
                    self.name_list.append(line[0])

            with open(dataset_config.train_scp_file_path + "utt2num_samples",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.num_samples_list.append(int(line[1]))

            with open(dataset_config.train_scp_file_path + "text",'r') as f:
                for line in f:
                    line = line.strip().split(' ',1)
                    if len(line) == 1:
                        self.label_list.append(None)
                    else:
                        self.label_list.append(line[1])

            # with open(dataset_config.train_scp_file_path + "my_ocr_text_type2",'r') as f:
            #     for line in f:
            #         line = line.strip().split(' ',1)
            #         if len(line) == 1:
            #             self.ocr_list.append(None)
            #         else:
            #             self.ocr_list.append(line[1])
      
            with open(dataset_config.train_scp_file_path + "hot_related/ocr_1gram_top50_mmr070_hotwords_list",'r') as f:
                for line in f:
                    line = line.strip().split()
                    if len(line) == 1:
                        self.ocr_list.append(None)
                    else:
                        line = line[1]
                        line = line.split('$')
                        line = " ".join(line)
                        self.ocr_list.append(line)


        elif split == "val":
            # 一次性load 全部数据
            # logger.info("loading validation audio data!")
            # scp_file = dataset_config.dev_scp_file_path + "my_wav.scp" 
            # with kaldiio.ReadHelper('scp:'+ scp_file) as reader:
            #     for key, numpy_array in tqdm(reader):
            #         self.data_list.append( numpy_array[1].astype(np.float32) )
            # logger.info("Finish loading!")

            with open(dataset_config.dev_scp_file_path + "my_wav.scp",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.data_list.append(line[1])
                    self.name_list.append(line[0])
            

            with open(dataset_config.dev_scp_file_path + "utt2num_samples",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.num_samples_list.append(int(line[1]))

            with open(dataset_config.dev_scp_file_path + "text",'r') as f:
                for line in f:
                    line = line.strip().split(' ',1)
                    if len(line) == 1:
                        self.label_list.append(None)
                    else:
                        self.label_list.append(line[1])

            # with open(dataset_config.dev_scp_file_path + "ocr_text_type2",'r') as f:
            #     for line in f:
            #         line = line.strip().split(' ',1)
            #         if len(line) == 1:
            #             self.ocr_list.append(None)
            #         else:
            #             self.ocr_list.append(line[1])

            with open(dataset_config.dev_scp_file_path + "hot_related/ocr_1gram_top50_mmr070_hotwords_list",'r') as f:
                for line in f:
                    line = line.strip().split()
                    if len(line) == 1:
                        self.ocr_list.append(None)
                    else:
                        line = line[1]
                        line = line.split('$')
                        line = " ".join(line)
                        self.ocr_list.append(line)

        elif split == "test":
            with open(dataset_config.test_scp_file_path + "my_wav.scp",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.data_list.append(line[1])      

            with open(dataset_config.test_scp_file_path + "my_wav.scp",'r') as f:
                for line in f:
                    line = line.strip().split()
                    self.num_samples_list.append(int(line[1]))

            with open(dataset_config.test_scp_file_path + "text",'r') as f:
                for line in f:
                    line = line.strip().split(' ',1)
                    if len(line) == 1:
                        self.label_list.append(None)
                    else:
                        self.label_list.append(line[1])

            with open(dataset_config.test_scp_file_path + "ocr_text_type2",'r') as f:
                for line in f:
                    line = line.strip().split(' ',1)
                    if len(line) == 1:
                        self.ocr_list.append(None)
                    else:
                        self.ocr_list.append(line[1])

        self.model_config = model_config
        self.dataset_config = dataset_config
        self.tokenizer = tokenizer
        self.IGNORE_INDEX = -100  # The default setting in CrossEntropyLoss
        self.prompt_template1 = "USER: {}\n ASSISTANT:"
        self.prompt_template2 = "USER: Transcribe speech to text. The speech is related to a slide, which contains key information. The text from the slide is \"{}\". Please use the text to enhance the accuracy of the ASR task.\n ASSISTANT:"
        self.answer_template = "{}"
        


    def __getitem__(self, index):
        ark_path = self.data_list[index]
        numpy_array = kaldiio.load_mat(ark_path)  #???
        audio_raw = numpy_array[1].astype(np.float32) #(12320,)  (103680,)
        #audio_raw = self.data_list[index]
        # audio_raw = torch.from_numpy(audio_raw).float()

        # num_samples = self.num_samples_list[index]  #12320
        # assert(audio_raw.shape[0] == num_samples)
        
        target = self.label_list[index]
        ocr = self.ocr_list[index]
        name = self.name_list[index]

        if self.model_config.encoder_name == "whisper":
            audio_raw = whisper.pad_or_trim(audio_raw)  #torch.Size([480000])
            audio_mel = whisper.log_mel_spectrogram(audio_raw).permute(1, 0)    #torch.Size([3000, 80])   torch.Size([648, 80])

        # if ocr == None:
        if self.dataset_config.use_ocr == True and ocr != None:
            prompt = self.prompt_template2.format(ocr)
        else:
            prompt = "Transcribe speech to text."
            prompt = self.prompt_template1.format(prompt)

        # 下面都一样
        answer = self.answer_template.format(target)

        prompt_ids = self.tokenizer.encode(prompt)

        prompt_length = len(prompt_ids)
        audio_length = (audio_mel.shape[0] + 1) // 2  # ad-hoc for whisper for 2x downsample from mel to feats
        audio_length = audio_length // 5 # ad-hoc for 5x fc downsample
        # audio_length = calculate_output_length_1d(audio_length, 5, 5, 0) # ad-hoc for 5x cov1d downsample
        # if self.fix_length_audio > 0:  #-1
        #     audio_length = self.fix_length_audio
        audio_pseudo = torch.full((audio_length,), -1) # placeholder

        example = prompt + answer  # FIX(MZY): avoid putting a bos token before answer.
        example_ids = self.tokenizer.encode(example)  # [prompt,answer]
        example_ids.append(self.tokenizer.eos_token_id)  # [prompt,answer,eos]



        example_ids = torch.tensor(
            example_ids, dtype=torch.int64
        )
        example_ids = torch.cat((audio_pseudo, example_ids))  # [audio,prompt,answer,eos]

        if len(example_ids)>1000:  #一维
            logger.info(name) 
            logger.info(audio_mel.shape)
            logger.info(audio_length)
            logger.info(prompt)
            logger.info(answer)
            logger.info(example_ids.shape)

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
            'audio_length': audio_length,
        }             


    def collator(self, samples):
        assert samples is not None
        input_ids_max_length = max([s['input_ids'].shape[0] for s in samples])
        input_ids = torch.stack([self.pad(s['input_ids'], input_ids_max_length, self.tokenizer.pad_token_id)
                                 for s in samples])
        labels = torch.stack([self.pad(s['labels'], input_ids_max_length, self.IGNORE_INDEX)
                              for s in samples])
        attention_mask = torch.stack([self.pad(s['attention_mask'], input_ids_max_length, False)
                                      for s in samples])
    
        audio_mel_max_length = max([s['audio_mel'].shape[0] for s in samples])
        audio_mel = torch.stack([self.pad(s['audio_mel'], audio_mel_max_length, 0)
                                  for s in samples])
        audio_mel_post_mask = torch.zeros(len(samples), (audio_mel_max_length + 1) // 2) # ad-hoc for whisper for 2x downsample from mel to feats
        for line, sample in enumerate(samples):
            audio_mel_post_mask[line, :(sample['audio_mel'].shape[0] + 1) // 2] = 1
    
        modality_mask = torch.zeros_like(attention_mask)
        for line, sample in enumerate(samples):
            modality_mask[line, :sample['audio_length']] = 1
    
        return {
            'input_ids': input_ids,
            'labels': labels,
            'attention_mask': attention_mask,
            'audio_mel': audio_mel,
            'audio_mel_post_mask': audio_mel_post_mask,
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
    dataset = SlidesDataset(dataset_config, model_config, tokenizer, split)
    return dataset



   