# 1. Move the raw unzipped data out of the way
mv mri_folder mri_folder_raw

# 2. Build a fresh mri_folder in the shape the script wants
mkdir -p mri_folder
for P in mri_folder_raw/P*/ ; do
  patient=$(basename "$P")                 # P01, P04a, etc.
  for tp_dir in "$P"BraTS/*/ ; do
    tp=$(basename "$tp_dir")               # baseline, fu1, fu2, …
    out="mri_folder/$patient/$tp"
    mkdir -p "$out"
    cp "$tp_dir"*.nii.gz "$out/"           # the 4 MRI sequences
    mask="$P""tumor segmentation/${patient}_tumor_mask_${tp}.nii.gz"
    if [ -f "$mask" ]; then
      cp "$mask" "$out/tumor_mask.nii.gz"
    else
      echo "WARN: no mask for $patient $tp"
    fi
  done
done

# 3. Sanity check — should list the 4 MRIs + 1 tumor_mask per timepoint
ls mri_folder/P01/baseline/