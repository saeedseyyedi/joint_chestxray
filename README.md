# joint_chestxray

Joint learning of chest radiographs and radiology reports in the application of pulmonary edema assessment.

This repository incorporates the algorithms presented in <br />
G. Chauhan<sup>\*</sup>, R. Liao<sup>\*</sup> et al. [Joint Modeling of Chest Radiographs and Radiology Reports for Pulmonary Edema Assessment.](https://arxiv.org/pdf/2008.09884.pdf) *International Conference on Medical Image Computing and Computer-Assisted Intervention*, 2020. <br />
(<sup>\*</sup> indicates equal contributions)

# Instructions

## Setup

Set up the conda environment using [`conda_environment.yml`](https://github.com/RayRuizhiLiao/joint_chestxray/blob/master/conda_environment.yml). You might want to remove the pip dependencies if that is creating an issue for you. You can manually install the spacy and scispacy dependencies using `pip install spacy` and `pip install scispacy`. Read [`https://allenai.github.io/scispacy/`](https://allenai.github.io/scispacy/) for more information on scispacy. 
     
## Training

Train the model in an unsupervised fashion, i.e., only the first term in [Eq (3)](https://arxiv.org/pdf/2008.09884.pdf) is optimized:

```
python ${repo_path}/scripts/main.py
--img_data_dir ${repo_path}/example_data/images/
--text_data_dir ${repo_path}/example_data/text/
--data_split_path ${repo_path}/example_data/data_split.csv
--use_text_data_dir
--use_data_split_path
--output_dir ${output_path}
--do_train
--training_folds 1 2 3 4 5 6
--training_mode 'semisupervised_phase1'
```

## Testing

# Notes on Data and Labels

## MIMIC-CXR

We have experimented this algorithm on [MIMIC-CXR](https://physionet.org/content/mimic-cxr/2.0.0/), which is a large publicly available dataset of chest radiographs in DICOM format with free-text radiology reports. The dataset contains 377,110 images corresponding to 227,835 radiographic studies performed at the Beth Israel Deaconess Medical Center in Boston, MA.

## Pulmonary edema severity

We have demonstrated the application of this algorithm in pulmonary edema assessment. We aim to classify a given chest x-ray image into one of the four ordinal levels: no edema (0), vascular congestion (1), interstitial edema (2), and alveolar edema (3).

## Regex and expert labeling

We use [regex](https://github.com/RayRuizhiLiao/regex_pulmonary_edema) to extract pulmonary edema severity labels from the radiology reports for our model training. A board-certified radiologist and two domain experts reviewed and labeled 485 radiology reports (corrsponsding to 531 chest radiographs). We use the expert labels for our model testing. The regex labeling results and expert labels on MIMIC-CXR are summerized [here](https://github.com/RayRuizhiLiao/joint_chestxray/blob/master/metadata/mimic-cxr-sub-img-edema-split-manualtest.csv).

## Data split

In our MICCAI 2020 work, we split the MIMIC-CXR data into training and test sets. There is no patient overlap between the training set and the test set. Our data split can be found [here](https://github.com/RayRuizhiLiao/joint_chestxray/blob/master/metadata/mimic-cxr-sub-img-edema-split-allCXR.csv). The folds 1-6 are the training set and the fold "TEST" is the test set. We also used the training set for cross-validation when tuning our model hyper-parameters.

# Contact

Geeticka Chauhan: geeticka [at] mit.edu <br />
Ruizhi Liao: ruizhi [at] mit.edu
