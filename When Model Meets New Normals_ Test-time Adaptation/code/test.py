######################################################
#                       _oo0oo_                      #
#                      o8888888o                     #
#                      88" . "88                     #
#                      (| -_- |)                     #
#                      0\  =  /0                     #
#                    ___/`---'\___                   #
#                  .' \\|     |// '.                 #
#                 / \\|||  :  |||// \                #
#                / _||||| -:- |||||- \               #
#               |   | \\\  -  /// |   |              #
#               | \_|  ''\---/''  |_/ |              #
#               \  .-\__  '-'  ___/-. /              #
#             ___'. .'  /--.--\  `. .'___            #
#          ."" '<  `.___\_<|>_/___.' >' "".          #
#         | | :  `- \`.;`\ _ /`;.`/ - ` : | |        #
#         \  \ `_.   \_ __\ /__ _/   .-` /  /        #
#     =====`-.____`.___ \_____/___.-`___.-'=====     #
#                       `=---='                      #
#                                                    #
#                                                    #
#     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    #
#                                                    #
#        Buddha Bless:   "No Bugs in my code"        #
#                                                    #
######################################################

import os
import wandb
import hydra
from omegaconf import DictConfig
import warnings; warnings.filterwarnings("ignore")

from utils.logger import make_logger
from utils.argpass import prepare_arguments
from utils.tools import SEED_everything
from utils.secret import WANDB_API_KEY, WANDB_PROJECT_NAME, WANDB_ENTITY

import torch
import pandas as pd
from ast import literal_eval
import json

from Exp import MLP_Tester, LSTMEncDec_Tester, USAD_Tester, THOC_Tester, AnomalyTransformer_Tester
from data.load_data import DataFactory


@hydra.main(version_base=None, config_path="cfgs", config_name="test_defaults")
def main(cfg: DictConfig) -> None:

    # prepare arguments
    args = prepare_arguments(cfg)

    # WANDB
    wandb.login(key=WANDB_API_KEY)
    wandb.init(project=WANDB_PROJECT_NAME, entity=WANDB_ENTITY, name=args.exp_id, mode="offline")
    wandb.config.update(args)

    # Logger
    logger = make_logger(os.path.join(args.log_path, f'{args.exp_id}_test.log'))
    logger.info("=== TESTING START ===")
    logger.info(f"Configurations: {args}")

    # SEED
    SEED_everything(args.SEED)
    logger.info(f"Experiment with SEED: {args.SEED}")

    # Data
    logger.info(f"Preparing {args.dataset} dataset...")
    datafactory = DataFactory(args, logger)
    train_dataset, train_loader, test_dataset, test_loader = datafactory()
    args.num_channels = train_dataset.X.shape[1]

    # Model
    logger.info(f"Loading pre-trained {args.model.name} model...")
    Testers = {
        "MLP": MLP_Tester,
        "LSTMEncDec": LSTMEncDec_Tester,
        "USAD": USAD_Tester,
        "THOC": THOC_Tester,
        "AnomalyTransformer": AnomalyTransformer_Tester,
    }

    tester = Testers[args.model.name](
        args=args,
        logger=logger,
        train_loader=train_loader,
        test_loader=test_loader,
        load=True,
    )

    # infer
    cols = ["tau", "Accuracy", "Precision", "Recall", "F1",  "tn", "fp", "fn", "tp"]
    cols += ["Accuracy_PA", "Precision_PA", "Recall_PA", "F1_PA", "tn_PA", "fp_PA", "fn_PA", "tp_PA"]
    cols += ["ROC_AUC", "PR_AUC"]
    result_df = pd.DataFrame([], columns=cols)
    for option in args.infer_options:
        result = tester.infer(mode=option, cols=cols)
        result_df = pd.concat([result_df, result])

    logger.info(f"\n{result_df.to_string()}")

    # log result
    wt = wandb.Table(dataframe=result_df)
    wandb.log({"result_table": wt})

if __name__ == "__main__":
    main()
