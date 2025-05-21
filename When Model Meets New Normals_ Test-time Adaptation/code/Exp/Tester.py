import torch
import numpy as np

import matplotlib
import matplotlib.pyplot as plt

import pickle
from utils.metrics import get_summary_stats
import os
from utils.tools import plot_interval, get_best_static_threshold

import wandb
import pandas as pd

import json
from ast import literal_eval

from sklearn.metrics import roc_curve, roc_auc_score
from utils.metrics import calculate_roc_auc, calculate_pr_auc
# from vus.metrics import get_range_vus_roc


matplotlib.rcParams['agg.path.chunksize'] = 10000


class Tester:
    '''
    Test-time logics,
    including offline evaluation and online adaptation.
    '''
    def __init__(self, args, logger, train_loader, test_loader):
        self.args = args
        self.logger = logger
        self.train_loader = train_loader
        self.test_loader = test_loader


    def calculate_anomaly_scores(self, dataloader):
        raise NotImplementedError()


    def checkpoint(self, filepath):
        self.logger.info(f"checkpointing: {filepath} @Trainer - torch.save")
        torch.save(self.model.state_dict(), filepath)


    def load(self, filepath):
        self.logger.info(f"loading: {filepath} @Trainer - torch.load_state_dict")
        self.model.load_state_dict(torch.load(filepath))
        self.model.to(self.args.device)


    def load_trained_model(self):
        self.load(os.path.join(self.args.checkpoint_path, f"best.pth"))


    @staticmethod
    def save_dictionary(dictionary, filepath):
        with open(filepath, "wb") as f:
            pickle.dump(dictionary, f)


    def prepare_stats(self):
        '''
        prepare anomaly scores of train data / test data.
        '''
        # train
        train_anoscs_pt_path = os.path.join(self.args.output_path, "train_anoscs.pt")
        if self.args.load_anoscs and os.path.isfile(train_anoscs_pt_path):
            self.logger.info("train_anoscs.pt file exists, loading...")
            with open(train_anoscs_pt_path, 'rb') as f:
                train_anoscs = torch.load(f)
                train_anoscs.to(self.args.device)
            self.logger.info(f"{train_anoscs.shape}")
        else:
            self.logger.info("train_anoscs.pt file does not exist, calculating...")
            train_anoscs = torch.Tensor(self.calculate_anomaly_scores(self.train_loader))  # (B, L, C) => (B, L)
            self.logger.info("saving train_anoscs.pt...")
            with open(train_anoscs_pt_path, 'wb') as f:
                torch.save(train_anoscs, f)
        torch.cuda.empty_cache()

        # test
        test_anosc_pt_path = os.path.join(self.args.output_path, "test_anoscs.pt")
        if self.args.load_anoscs and os.path.isfile(test_anosc_pt_path):
            self.logger.info("test_anoscs.pt file exists, loading...")
            with open(test_anosc_pt_path, 'rb') as f:
                test_anoscs = torch.load(f)
                test_anoscs.to(self.args.device)
            self.logger.info(f"{test_anoscs.shape}")
        else:
            self.logger.info("test_anoscs.pt file does not exist, calculating...")
            test_anoscs = torch.Tensor(self.calculate_anomaly_scores(self.test_loader))  # (B, L, C) => (B, L)
            self.logger.info("saving test_anoscs.pt...")
            with open(test_anosc_pt_path, 'wb') as f:
                torch.save(test_anoscs, f)
        torch.cuda.empty_cache()

        # train_anoscs, test anoscs (T=B*L, ) and ground truth
        train_mask = (self.train_loader.dataset.y != -1)
        self.train_anoscs = train_anoscs.detach().cpu().numpy()[train_mask] # does not include -1's
        self.test_anoscs = test_anoscs.detach().cpu().numpy() # may include -1's, filtered when calculating final results.
        self.gt = self.test_loader.dataset.y

        # thresholds for visualization
        self.th_q95 = np.quantile(self.train_anoscs, 0.95)
        self.th_q99 = np.quantile(self.train_anoscs, 0.99)
        self.th_q100 = np.quantile(self.train_anoscs, 1.00)
        self.th_off_f1_best = get_best_static_threshold(gt=self.gt, anomaly_scores=self.test_anoscs)


    def infer(self, mode, cols):
        result_df = pd.DataFrame(columns=cols)
        gt = self.test_loader.dataset.y

        # for single inference: select specific threshold tau
        th = self.args.thresholding
        if th[0] == "q":
            th = float(th[1:]) / 100
            tau = np.quantile(self.train_anoscs, th)
        elif th == "off_f1_best":
            tau = self.th_off_f1_best
        else:
            raise ValueError(f"Thresholding mode {self.args.thresholding} is not supported.")

        # get result
        if mode == "offline":
            anoscs, pred = self.offline(tau)
            result = get_summary_stats(gt, pred)
            roc_auc = calculate_roc_auc(gt, anoscs,
                                        path=self.args.output_path,
                                        save_roc_curve=self.args.save_roc_curve,
                                        drop_intermediate=False
                                        )
            pr_auc = calculate_pr_auc(gt, anoscs,
                                      path=self.args.output_path,
                                      save_pr_curve=self.args.save_pr_curve,
                                      )
            result["ROC_AUC"] = roc_auc
            result["PR_AUC"] = pr_auc

            result_df = pd.DataFrame([result], index=[mode], columns=result_df.columns)
            result_df.at[mode, "tau"] = tau


        elif mode == "online":
            anoscs, pred = self.online(self.test_loader, tau, normalization=self.args.normalization)
            result = get_summary_stats(gt, pred)
            roc_auc = calculate_roc_auc(gt, anoscs,
                                        path=self.args.output_path,
                                        save_roc_curve=self.args.save_roc_curve,
                                        drop_intermediate=False,
                                        )
            result["ROC_AUC"] = roc_auc

            pr_auc = calculate_pr_auc(gt, anoscs,
                                      path=self.args.output_path,
                                      save_pr_curve=self.args.save_pr_curve,
                                      )
            result["PR_AUC"] = pr_auc

            wandb.log(result)
            result_df = pd.DataFrame([result], index=[mode], columns=result_df.columns)
            result_df.at[mode, "tau"] = tau


        if self.args.save_result:
            filename = f"{self.args.exp_id}_{mode}_{th}" if (not hasattr(self.args, "qStart")) \
                else f"{self.args.exp_id}_{mode}_{self.args.qStart}_{self.args.qEnd}_{self.args.qStep}"
            path = os.path.join(self.args.result_path, filename+".csv")
            self.logger.info(f"Saving dataframe to {path}")
            result_df.to_csv(path)

            if len(result_df) == 1:
                result_dict = literal_eval(result_df.reset_index(drop=True).to_json(orient="index"))['0']
                # save as unique id
                with open(os.path.join(self.args.result_path, filename+".json"), "w") as f:
                    self.logger.info(f"Saving json to {path}")
                    json.dump(result_dict, f)
                # save as "result.json", for convenience
                with open(os.path.join(self.args.result_path, "result.json"), "w") as f:
                    json.dump(result_dict, f)

        self.logger.info(f"{mode} \n {result_df.to_string()}")
        return result_df


    def offline(self, tau):
        pred = (self.test_anoscs >= tau)

        # plot results
        plt.figure(figsize=(20, 6), dpi=500)
        plt.plot(self.test_anoscs, color="blue", label="anomaly score w/o online learning")
        plt.axhline(self.th_q95, color="C1", label="Q95 threshold")
        plt.axhline(self.th_q99, color="C2", label="Q99 threshold")
        plt.axhline(self.th_q100, color="C3", label="Q100 threshold")
        plt.axhline(self.th_off_f1_best, color="C4", label="threshold w/ test data")

        plot_interval(plt, self.gt)
        plot_interval(plt, pred, facecolor="gray")
        plt.legend()
        plt.savefig(os.path.join(self.args.plot_path, f"{self.args.exp_id}_offline.png"))
        wandb.log({f"{self.args.exp_id}_offline": wandb.Image(plt)})

        return self.test_anoscs, pred


    def online(self, *args):
        raise NotImplementedError()