# pyRadiomicBM
<p align="center">
  <a href="https://in-silico-modelling.ucy.ac.cy"><img src="https://img.shields.io/badge/In%20Silico%20Modelling%20Group-green"/></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"/></a>
</p>
A comprehensive Python-based radiomic analysis pipeline on magnetic resonance imaging data of brain metastases (BM)

## Installation 
Conda environment name: achcmu
Once conda environment is activated, run the following: 
`pip install git+https://github.com/AIM-Harvard/pyradiomics.git@v3.1.0`
`pip install -r requirements.txt` 

Download the patient data from https://zenodo.org/records/23171182?preview_file=P01.zip into `mri_folder_raw`.

The script expects the following file directory structure: 
```
mri_folder/
└── P01/                 ← first-level ✓
    ├── baseline/        ← second-level ✓
    │   ├── t1.nii.gz
    │   ├── t1c.nii.gz
    │   ├── t2.nii.gz
    │   ├── fla.nii.gz
    │   └── tumor_mask.nii.gz    ← mask alongside images ✓
    ├── fu1/
    │   └── (same 5 files)
    ├── fu2/ …
    ├── fu3/ …
    └── fu4/ …
```

The paper’s data on Zenodo uses the following structure instead, which is different from what the script expects:
```
mri_folder/
└── P01/
    ├── BraTS/                        ← extra level the README doesn't expect
    │   └── baseline/
    │       ├── t2.nii.gz
    │       ├── t1c.nii.gz
    │       ├── t1.nii.gz
    │       └── fla.nii.gz             ← no mask in this folder
    ├── tumor segmentation/           ← masks live in a DIFFERENT folder
    │   └── P01_tumor_mask_baseline.nii.gz
    ├── P01_RTP.nii.gz                ← stray files at the case level
    ├── P01_CT.nii.gz
    ├── P01_brain_mask.nii.gz
    └── DICOM/                        ← ignore (not .nii.gz)
```
. To reorganize the data to be the structure the script expects, run the following: 
`bash data_reorg.sh` 

Finally, run `python run.py`.

## Description of pipeline
### Data: 
* Image file (NIfTI file, `.nii` or `.nii.gz`) with signal intensities from MRI scan  
* Mask file (NIfTI file) with labels in voxels with tumor, labelled by radiologist 

### Feature extraction pipeline:
1. Read data using `sitk.ReadImage`
2. N4 bias field correction 
- MRI scans don't produce uniformly-lit images 
3. Clip intensity of voxels between 0.1th and 99.9th percentile 
4. Linearly rescale voxels to [0, 1024]
5. Use mask to crop image to smallest 3D box containing the tumor 
6. PyRadiomics takes in (processed_image, mask) and outputs: 
  - First-order statistics (~19 features): mean, standard deviation, skewness, kurtosis, entropy, energy, etc. 
  - Shape (~16 features): "what does the tumor look like?" volume, surface area, etc. 
  - Gray Level Co-occurrence Matrix (GLCM) (~24 features): for every pair of neighboring voxels, how often does intensity a sit next to intensity b? Builds a 2D histogram of neighbor pairs, then computes derived numbers like contrast, correlation, homogeneity. Captures fine-grained texture.
  - GLRLM — Gray Level Run Length Matrix (~16 features): how long are the “runs” of same-intensity voxels along each direction? Long runs = smooth homogeneous regions; short runs = noisy or textured.
  - GLSZM — Gray Level Size Zone Matrix (~16 features): similar idea but counts connected 3D zones of similar intensity. Big zones = big uniform patches; small zones = speckled texture.
  - NGTDM — Neighbouring Gray Tone Difference Matrix (~5 features): for each voxel, how different is its intensity from the average of its neighborhood? Summarizes “busyness” and “coarseness” of the texture.
  - GLDM — Gray Level Dependence Matrix (~14 features): for each voxel, how many neighbors have similar intensity? Measures local uniformity.
7. Save to one DataFrame per patient, saved as `{patient_id}_{mask_region}_{modality}_{timepoint}_{feature_name}`

## How to use
The pyRadiomicBM project is built using Python. 

Function "my_main_funct" calculates the radiomics features from multiple MRIs. It takes as input parameter "mri_folder" (str).

Input: "mri_folder" (str): The path to the folder containing the MR images and their corresponding masks (annotations). The structure of the folder needs to be the following:

1) "mri_folder" is the main folder, containing all MR images (**first level subfolders**)
2) first level subfolders: Case-specific folders, containing subfolders where MRI data from different acquisition times are stored (e.g. case1, case2, etc.) (**second level subfolders**)
3) second level subfolders: Acquisition time specific folders containg MRI and their corresponding mask (**third level subfolders**)
4) third level subfolders: Folders that store the MRI data (e.g. T2flair.nii.gz, T1.nii.gz, etc.) along with their corresponding mask (e.g. tumour_mask.nii.gz) 

Example: **main folder** "mri_folder" --> **first level subfolder** "case1" --> **second level subfolder** "baseline" --> **Image files** (T2flair.nii.gz // T1c.nii.gz // tumor_mask.nii.gz)

## License
The pyRadiomicBM project is [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.txt) licensed.

## Acknowledgements
This work was financially supported by the Cyprus Cancer Research Institute through the PROTEAS project (Call: Bridges in Research Excellence CCRI_2020_FUN_001; Grant ID: CCRI_2021_FA_LE_105). 

Part of the image pre-processing has been implemented using the MAMA-MIA GitHub repository (https://github.com/LidiaGarrucho/MAMA-MIA)

<p align="center">
      <img src="./docs/CCRI-logo.png" align="left" height="100">
      <img src="./docs/PROTEAS-logo.png" align="right" height="100">
</p>
