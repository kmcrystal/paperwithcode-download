#!/bin/bash
# AnomalyTransformer

echo "GPU $1"
for SEED in 2021 2022 2023 2024 2025
do
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=SWaT window_size=100 stride=100 eval_stride=100 batch_size=256 eval_batch_size=256 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=WADI window_size=100 stride=100 eval_stride=100 batch_size=256 eval_batch_size=256 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=SMD +dataset_id=machine-1-4 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=SMD +dataset_id=machine-2-1 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=MSL +dataset_id=P-15 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=1.0
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=SMAP +dataset_id=T-3 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=1.0
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=CreditCard window_size=100 stride=100 eval_stride=100 batch_size=256 eval_batch_size=256 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=yahoo +dataset_id=real_20 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
  CUDA_VISIBLE_DEVICES=$1 python train.py SEED=$SEED dataset=yahoo +dataset_id=real_55 window_size=100 stride=100 eval_stride=100 batch_size=1 eval_batch_size=1 normalization=None model=AnomalyTransformer model.anomaly_ratio=0.5
done