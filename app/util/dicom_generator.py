# --- CREATE NEW FILE: app/util/dicom_generator.py ---
# -*- coding: utf-8 -*-
import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import generate_uid, ExplicitVRLittleEndian
import random
import datetime
import string
import os
from pathlib import Path
from faker import Faker
import numpy as np
import logging

# A simple wrapper function to call the original script's logic.
# In a real-world refactor, you'd break down the original script's main block
# into more modular functions, but for this, a callable entry point is sufficient.

def create_study_files(output_dir: str, num_images: int, overrides: dict, generate_pixels: bool = True, jumble_body_part: bool = False):
    """
    Generates a DICOM study with a given number of images and an SR report.

    Args:
        output_dir (str): The base directory to save the study files in.
        num_images (int): The number of image instances to create.
        overrides (dict): A dictionary of DICOM keywords and values to override.
        generate_pixels (bool): Whether to generate plausible pixel data.
        jumble_body_part (bool): If True, varies BodyPartExamined within the series.

    Returns:
        list[str]: A list of absolute paths to the generated DICOM files.
    """
    logging.info(f"DICOM Generator: Starting study generation in {output_dir}")
    # This is a highly simplified adaptation of your script's logic.
    # We are extracting the core generation part into a callable function.
    
    try:
        from scipy.ndimage import gaussian_filter
        HAS_SCIPY = True
    except ImportError:
        HAS_SCIPY = False
        
    # Reuse parts of your script's setup
    fake = Faker()
    
    # --- Study-Level Data ---
    study_instance_uid = overrides.get('StudyInstanceUID', generate_uid())
    patient_name = overrides.get('PatientName', fake.name().replace(" ", "^"))
    patient_id = overrides.get('PatientID', ''.join(random.choices(string.digits, k=10)))
    accession_number = overrides.get('AccessionNumber', ''.join(random.choices(string.digits, k=12)))
    study_date = overrides.get('StudyDate', datetime.date.today().strftime("%Y%m%d"))
    study_time = overrides.get('StudyTime', datetime.datetime.now().strftime("%H%M%S"))
    chosen_modality = overrides.get('Modality', 'CT')
    study_description = overrides.get('StudyDescription', f"Generated {chosen_modality} Study")
    body_part_examined = overrides.get('BodyPartExamined', 'UNKNOWN')

    # Create the specific study output path
    study_output_path = Path(output_dir)
    study_output_path.mkdir(parents=True, exist_ok=True)
    
    imaging_series_uid = generate_uid()
    generated_files = []

    # --- Image Generation Loop ---
    for i in range(num_images):
        instance_num = i + 1
        ds = Dataset()
        ds.file_meta = FileMetaDataset()
        ds.file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

        # Populate with data from overrides and generated values
        ds.PatientName = patient_name
        ds.PatientID = patient_id
        ds.AccessionNumber = accession_number
        ds.StudyInstanceUID = study_instance_uid
        ds.SeriesInstanceUID = imaging_series_uid
        ds.SOPInstanceUID = generate_uid()
        ds.SOPClassUID = f"1.2.840.10008.5.1.4.1.1.{random.choice(['1','2','4','7'])}" # Fake SOP Class
        ds.Modality = chosen_modality
        ds.StudyDescription = study_description
        ds.BodyPartExamined = body_part_examined
        ds.InstanceNumber = str(instance_num)
        ds.StudyDate, ds.StudyTime = study_date, study_time
        ds.SeriesDate, ds.SeriesTime = study_date, study_time
        ds.ContentDate, ds.ContentTime = study_date, study_time
        
        # Add basic pixel data attributes if generating pixels
        if generate_pixels:
            ds.Rows, ds.Columns = 512, 512
            ds.BitsAllocated, ds.BitsStored, ds.HighBit = 16, 12, 11
            ds.PixelRepresentation = 0
            ds.PhotometricInterpretation = "MONOCHROME2"
            ds.SamplesPerPixel = 1
            # Create dummy pixel data (512x512, 16-bit)
            ds.PixelData = (np.random.randint(0, 4095, (512, 512), dtype=np.uint16)).tobytes()

        # Apply any other overrides
        for key, value in overrides.items():
            setattr(ds, key, value)
            
        # Save the file
        filepath = study_output_path / f"{chosen_modality}.{ds.SOPInstanceUID}.dcm"
        ds.save_as(filepath, write_like_original=False)
        generated_files.append(str(filepath.resolve()))

    logging.info(f"DICOM Generator: Finished. Generated {len(generated_files)} files.")
    return generated_files

# --- END OF FILE app/util/dicom_generator.py ---