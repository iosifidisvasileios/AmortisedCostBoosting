import warnings
warnings.filterwarnings("ignore")

import operator

from sklearn.metrics import f1_score

from Competitors.AdaC1C3 import AdaCost
from Competitors.RareBoost import RareBoost
from DataPreprocessing.load_diabetes import load_diabetes
from DataPreprocessing.load_electricity import load_electricity
from DataPreprocessing.load_phoneme import load_phoneme
from DataPreprocessing.load_speed_dating import load_speed_dating


from DataPreprocessing.load_mat_data import load_mat_data

import pickle
from collections import Counter
import os, sys
from multiprocessing import Process
from imblearn import datasets
from AdaCC import AdaCC
from DataPreprocessing.load_adult import load_adult
from DataPreprocessing.load_wilt import load_wilt
from DataPreprocessing.load_mushroom import load_mushroom
from DataPreprocessing.load_eeg_eye import load_eeg_eye
from DataPreprocessing.load_spam import load_spam
from DataPreprocessing.load_skin import load_skin
from DataPreprocessing.load_credit import load_credit
from DataPreprocessing.load_kdd import load_kdd
from DataPreprocessing.load_bank import load_bank
from plot_functions import plot_costs_per_round, \
    plot_costs_per_round_all_datasets

sys.path.insert(0, 'DataPreprocessing')


def update_stats(new_stats, RareBoostFlag):
    output = dict()

    output['pos_class_weights'] = new_stats[0]
    output['neg_class_weights'] = new_stats[1]
    output['bal_err'] = new_stats[2]
    if RareBoostFlag:
        output['alpha_positive'] = new_stats[3]
        output['alpha_negative'] = new_stats[4]
    else:
        output['alpha'] = new_stats[3]

    return output


def print_stats(names, stats):
    for i in range(0, len(names)):
        print(names[i] + " " + str(stats[i]))


def run_eval(dataset, baseL, methods):
    if dataset == "wilt":
        X, y, cl_names = load_wilt()
    elif dataset == "adult":
        X, y, cl_names = load_adult()
    elif dataset == "diabetes":
        X, y, cl_names = load_diabetes()
    elif dataset == "phoneme":
        X, y, cl_names = load_phoneme()
    elif dataset == "mushroom":
        X, y, cl_names = load_mushroom()
    elif dataset == "electricity":
        X, y, cl_names = load_electricity()
    elif dataset == "speeddating":
        X, y, cl_names = load_speed_dating()
    elif dataset == "credit":
        X, y, cl_names = load_credit()
    elif dataset == "eeg_eye":
        X, y, cl_names = load_eeg_eye()
    elif dataset == "spam":
        X, y, cl_names = load_spam()
    elif dataset == "skin":
        X, y, cl_names = load_skin()
    elif dataset == "bank":
        X, y, cl_names = load_bank()
    elif dataset == "kdd":
        X, y, cl_names = load_kdd()
    elif dataset == "landsatM":
        X, y, cl_names = load_mat_data(dataset)
    elif dataset == "musk2":
        X, y, cl_names = load_mat_data(dataset)
    elif dataset == "spliceM":
        X, y, cl_names = load_mat_data(dataset)
    elif dataset == "semeion_orig":
        X, y, cl_names = load_mat_data(dataset)
    elif dataset == "waveformM":
        X, y, cl_names = load_mat_data(dataset)
    else:
        data = datasets.fetch_datasets()[dataset]
        cl_names = ["feature_" + str(i) for i in range(0, data['data'].shape[1])]
        X = data['data']
        y = data['target']

    y[y != 1] = 0
    print("===============-- " + dataset + " --===============")

    processes = []
    for method in methods:
        p = Process(target=train_and_predict, args=(X, y, baseL, method))
        p.start()
        processes.append(p)

    for p in processes:
        p.join()

    list_of_dicts = []

    for method in methods:
        if method == "RareBoost":
            with open('temp_preds_AdaCC/' + method, 'rb') as filehandle:
                list_of_dicts.append(update_stats(pickle.load(filehandle), True))
        else:
            with open('temp_preds_AdaCC/' + method, 'rb') as filehandle:
                list_of_dicts.append(update_stats(pickle.load(filehandle), False))

    plot_costs_per_round(methods, list_of_dicts, baseL, "Images/PerRoundBaselines/" + dataset + "/")
    return list_of_dicts


def train_and_predict(X_train, y_train, base_learners, method):
    if method == 'AdaBoost':
        clf = AdaCost(algorithm='AdaBoost', n_estimators=base_learners, debug=True)
        clf.fit(X_train, y_train)
    elif 'AdaCC' in method:
        clf = AdaCC(n_estimators=base_learners, algorithm=method, debug=True)
        clf.fit(X_train, y_train)
    elif 'AdaN-AC' in method:
        clf = AdaCC(n_estimators=base_learners, algorithm=method.replace("N-", ""), debug=True, amortised=False)
        clf.fit(X_train, y_train)
    elif 'RareBoost' in method:
        clf = RareBoost(n_estimators=base_learners, debug=True)
        clf.fit(X_train, y_train)
        with open('temp_preds_AdaCC/' + method, 'wb') as filehandle:
            pickle.dump([clf._class_weights_pos, clf._class_weights_neg, clf.training_error, clf.estimator_weights_pos,
                         clf.estimator_weights_neg], filehandle)
        return
    else:
        counter_dict = Counter(list(y_train))

        majority = max(counter_dict.items(), key=operator.itemgetter(1))[0]
        minority = max(counter_dict.items(), key=operator.itemgetter(0))[0]
        best = -1
        ratios = [1., 2., 3., 4., 5., 6., 7, 8., 9., 10.]
        # ratios = [2.5, 5., 7.5, 10.]

        for j in ratios:
            try:
                clf = AdaCost(n_estimators=base_learners, algorithm=method,
                              class_weight={minority: 1, majority: j / 10.},
                              debug=True)
                clf.fit(X_train, y_train)
                if clf.error == 1:
                    continue

                temp = f1_score(y_train, clf.predict(X_train))
                if temp >= best:
                    best = temp
                    best_clf = clf
            except:
                pass
        clf = best_clf

    with open('temp_preds_AdaCC/' + method, 'wb') as filehandle:
        pickle.dump([clf._class_weights_pos, clf._class_weights_neg, clf.training_error, clf.estimator_alphas_],
                    filehandle)


if __name__ == '__main__':

    if not os.path.exists("Images"):
        os.makedirs("Images")

    if not os.path.exists("Images/PerRoundBaselines"):
        os.makedirs("Images/PerRoundBaselines")

    if not os.path.exists("temp_preds_AdaCC"):
        os.makedirs("temp_preds_AdaCC")

    baseLearners = [200]
    list_of_methods = ['AdaBoost', 'AdaCC1', 'AdaCC2', 'AdaCost', 'CSB1', 'CSB2', 'AdaC1', 'AdaC2', 'AdaC3', 'RareBoost']

    # datasets_list = sorted(['mushroom', 'adult', 'wilt', 'credit', 'spam', 'bank', 'landsatM', 'musk2', 'isolet',
    #                         'spliceM', 'semeion_orig', 'waveformM', 'abalone', 'car_eval_34', 'letter_img',
    #                         'skin', 'eeg_eye', 'phoneme', 'electricity', 'scene',  # 'kdd' ,'diabetes',
    #                         'mammography', 'optical_digits', 'pen_digits', 'satimage', 'sick_euthyroid', 'thyroid_sick',
    #                         'wine_quality', 'us_crime', 'protein_homo', 'ozone_level', 'webpage', 'coil_2000'])
    datasets_list = sorted(['adult', 'wilt', 'credit', 'spam', 'bank', 'musk2', 'isolet',
                            'abalone', 'car_eval_34', 'letter_img',
                            'skin', 'eeg_eye', 'phoneme', 'electricity', 'scene',
                            'mammography', 'optical_digits', 'pen_digits', 'satimage', 'sick_euthyroid', 'thyroid_sick',
                            'wine_quality', 'us_crime', 'ozone_level', 'webpage', 'coil_2000'])
    for baseL in baseLearners:
        dicts_for_plots = []
        for dataset in datasets_list:
            dicts_for_plots.append(run_eval(dataset=dataset, baseL=baseL, methods=list_of_methods))

        plot_costs_per_round_all_datasets(list_of_methods, dicts_for_plots, "Images/PerRoundBaselines/Overall/", baseL)
